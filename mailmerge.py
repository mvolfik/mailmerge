import os
import re
import subprocess
import sys
from argparse import ArgumentParser
from email.message import EmailMessage
from mimetypes import guess_type
from smtplib import SMTP_SSL
from tempfile import NamedTemporaryFile
from typing import List, Dict, Optional, NewType, Any

import frontmatter
import jinja2
import pydantic
from bs4 import BeautifulSoup
from markdown import Markdown
from pydantic import Field
from pydantic.main import BaseModel

loader = jinja2.FileSystemLoader("includes")

html_renderer = jinja2.Environment(loader=loader, lstrip_blocks=True, trim_blocks=True)
html_renderer.filters["md"] = Markdown(extensions=["tables"]).convert
html_renderer.globals["txt"] = False

txt_renderer = jinja2.Environment(loader=loader, lstrip_blocks=True, trim_blocks=True)
txt_renderer.filters["md"] = lambda x: x
txt_renderer.globals["txt"] = True

# in yaml:
# fields:
#   some_text: >
#     First paragraph
#     multiline ok
#
#     Second paragraph
#
#   more: stuff
#
# this is processed as 'First paragraph multiline ok\nSecond paragraph', so you need to pass it through this filter for correct rendering
html_renderer.filters["fix_newlines"] = txt_renderer.filters[
    "fix_newlines"
] = lambda x: "\n\n".join(x.splitlines())


class InputError(Exception):
    pass


Headers = NewType("Headers", Dict[str, str])
Attachments = NewType("Attachments", List[str])
Fields = NewType("Fields", Dict[str, Any])


class Recipient(BaseModel):
    class Config:
        allow_mutation = False

    address: str
    fields: Fields


class CampaignData(BaseModel):
    class Config:
        allow_mutation = False

    attachments: Attachments = Field(default_factory=list)
    headers: Headers
    recipients: List[Recipient]


class SenderConfig(BaseModel):
    class Config:
        allow_mutation = False

    headers: Headers
    server: str
    login: str
    pwd: str
    override_recipient: Optional[str]


SenderConfigFile = Dict[str, SenderConfig]


@pydantic.validate_arguments
def _create_message(
    recipient: str,
    headers: Headers,
    html: str,
    txt: str,
    attachments: Attachments,
) -> EmailMessage:
    if any(x not in headers for x in ("From", "Subject")):
        raise InputError(
            "You need to provide From and Subject of the mail in the headers field"
        )

    msg = EmailMessage()
    for k, v in headers.items():
        msg[k] = v
    msg["To"] = recipient
    msg.set_content(txt, subtype="plain")
    msg.add_alternative(html, subtype="html")

    for attachment in attachments:
        typ = guess_type(attachment)[0]
        if typ is None:
            raise InputError(
                f"Couldn't detect mimetype for {attachment}. Does it have correct extension set?"
            )
        maintype, subtype = typ.split("/", 1)
        with open(attachment, "rb") as fh:
            msg.add_attachment(
                fh.read(),
                filename=os.path.basename(attachment),
                maintype=maintype,
                subtype=subtype,
            )

    return msg


@pydantic.validate_arguments
def _confirm_overall(
    sender_config: SenderConfig, headers: Headers, attachments: Attachments
) -> bool:
    print("Sending emails with this config:")
    print(f"  - logging in as {sender_config.login} to {sender_config.server}")
    print()
    print("  - sending with these headers (check From, Subject AND CC):")
    for name, value in headers.items():
        print(f"      {name}: '{value}'")
    print()
    if attachments:
        print("  - sending the following attachments:")
        for att in attachments:
            print(f"    - '{att}'")
    else:
        print("  - there are NO ATTACHMENTS")
    print()
    return input("PLEASE DOUBLE-CHECK EVERYTHING and type 'yes' to proceed: ") == "yes"


@pydantic.validate_arguments
def _confirm_one(
    recipient_data: Recipient,
    headers: Headers,
    txt: str,
    html: str,
    override_recipient: Optional[str],
) -> bool:
    with NamedTemporaryFile("wt") as f:
        f.write(
            f"<!doctype html><html><head><meta charset='utf-8'/><title>E-mail preview</title></head><body><p>To: {recipient_data.address}</p><p>{headers['Subject']}</p><hr/>{html}</body></html>"
        )
        f.flush()
        subprocess.run(["firefox", f.name])
        print("=" * 50)
        print(txt)
        print("======")
        print(
            f"Sending the above email to {recipient_data.address}."
            if override_recipient is None
            else f"This would be sent to {recipient_data.address}, but sender config overrides all sending to {override_recipient}."
        )
        return input("Type 'yes' to proceed: ") == "yes"


@pydantic.validate_arguments
def main(
    campaign: str,
    sender_config: SenderConfig,
    confirmations: bool = False,  # default for function is False, but default for CLI is True
) -> int:
    with open(f"mails/{campaign}.txt") as fh:
        content = frontmatter.load(fh)

    html_template = html_renderer.from_string(content.content)
    txt_template = txt_renderer.from_string(content.content)

    data = CampaignData.parse_obj(content.metadata)

    headers = data.headers
    headers.update(sender_config.headers)
    attachments = data.attachments
    override_recipient = sender_config.override_recipient

    if confirmations:
        if not _confirm_overall(sender_config, headers, attachments):
            print("Confirmation failed, exiting", file=sys.stderr)
            return 1

    with SMTP_SSL(sender_config.server) as conn:
        conn.login(sender_config.login, sender_config.pwd)

        for recipient_data in data.recipients:
            soup = BeautifulSoup(
                html_template.render(recipient_data.fields), features="html.parser"
            )

            body = soup.find(id="main-body")
            for p in body.find_all("p", recursive=False):
                p.attrs["style"] = "margin:0.6em 0;line-height:1.4"
            for p in body.find_all(re.compile("^h[1-9]$"), recursive=False):
                p.attrs["style"] = "margin:0.8em 0 0;font-size:1.1em"
            for p in body.select("li > p"):
                p.attrs["style"] = "margin-bottom:0;"
            for p in body.select(":scope > ul > li"):
                p.attrs["style"] = "margin-top:0.5em;"

            html = str(soup)

            txt = txt_template.render(recipient_data.fields)

            if confirmations:
                if not _confirm_one(
                    recipient_data, headers, txt, html, override_recipient
                ):
                    print("Not confirmed, skipping", file=sys.stderr)
                    continue

            msg = _create_message(
                override_recipient or recipient_data.address,
                headers,
                html,
                txt,
                data.attachments,
            )

            conn.send_message(msg)
            print("Sent.")
    print("Done.")
    return 0


def cli() -> None:
    with open("senderconfig.json") as fh:
        senderconfig = pydantic.parse_raw_as(SenderConfigFile, fh.read())

    argparser = ArgumentParser()
    argparser.add_argument(
        "campaign", help="The name of the file to use (`mails/<campaign>.txt`)"
    )
    argparser.add_argument(
        "--sender", choices=senderconfig.keys(), help="Name of the senderconfig to use"
    )
    argparser.add_argument(
        "--no-confirmations",
        action="store_false",
        default=True,
        dest="confirmations",
        help="I exactly know what I'm doing, just send everything immediately.",
    )
    args = argparser.parse_args()
    sender_name = args.sender
    if sender_name is None:
        print("Please select a sender configuration:")
        print()
        for name, data in senderconfig.items():
            print(
                "  [{}]: {}".format(
                    name, ", ".join(f"{k}: '{v}'" for k, v in data.headers.items())
                )
                + (
                    f"; mock send to {data.override_recipient}"
                    if data.override_recipient is not None
                    else ""
                )
            )
        print()
        sender_name = input("Your selection: ")
        if sender_name not in senderconfig.keys():
            print("Invalid selection", file=sys.stderr)
            sys.exit(1)
        print()

    sys.exit(main(args.campaign, senderconfig[sender_name], args.confirmations))


if __name__ == "__main__":
    cli()
