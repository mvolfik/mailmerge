# A simple mailmerge written in Python

It uses [Jinja2 templating][1], so you can use all kinds of fancy syntax to do introduce various logic. Most
importantly, a markdown filter is available, but you can also use conditional expressions and blocks, for example to use
a different signature for the plaintext and html versions of the mail. See `templates/example.md`
and `data/example.yaml` for an example email.

Plaintext and HTML versions of the email are always generated. The markdown filter does nothing in the plaintext
version, so it's not that pretty, but who sees that nowadays. Maybe some nerds who understand markdown anyways :)

[1]: https://jinja.palletsprojects.com/templates/

## Usage

### Install environment

```shell
python3 -m virtualenv .venv
. .venv/bin/activate.fish
pip install -r requirements.txt
```

### Configure sender

Create the file `senderconfig.json`, which contains a dictionary of config names and their data.

The following fields are available (see `example-senderconfig.json` for an example):

- `headers`: these are simply copied into the email
- `server`, `login` and `pwd`: SMTP server and credentials used to send emails with this config
- `override_recipient`: if this field is present, no emails are actually sent to the target addresses, everything is set
  to this address instead
    - **beware: nothing is done about `CC` and other headers** that might affect sending, so preferrably set these in
      sender config, not in the individual campaign data files)

### Create your template and data file

Create your own template (and signatures etc) and campaign data file. They need to have the same name, let's
say `templates/campaign.md` and `data/campaign.yaml`. Template is a Jinja2 template, see `templates/example.md`. In data
file, you can configure the following:

- global `headers`: again, these are copied directly – you likely want to specify `Subject` here
    - if there's a header with the exactly same name in sender config and campaign, the sender config one is preferred
- global `attachments` are paths to files to be added to every email as attachments (I didn't need per-sender
  attachments yet, so these aren't implemented)
- `recipients`: a list of recipients with the following properties
    - `address` will be added as a `To` header
    - `fields` is a dictionary, the values are passed directly into the template, so you can make use of various
      structures

### Finally, the CLI

```
$ python3 mailmerge.py -h
usage: mailmerge.py [-h] [--sender {your,created,senderconfigs}] [--no-confirmations] campaign

positional arguments:
  campaign              The name of the data file + template to send

optional arguments:
  -h, --help            show this help message and exit
  --sender {your,created,senderconfigs}
                        Name of the senderconfig to use
  --no-confirmations    I exactly know what I'm doing, just send everything immediately.
```

If sender isn't provided, you will be asked interactively. Campaign is the common tame of the templates and data file,
i.e. `example` for what we chose above. If `--no-confirmations` isn't provided, you will be prompted to confirm campaign
data overall, and then you will be shown a preview of each email (both plaintext on stdout and HTML in browser). If you
don't confirm the campaign, the program will exit, emails you don't confirm are skipped.

## Caveats

Beware of newline issues happening anywhere around yaml, jinja and markdown. For example, the following yaml data:

```yaml
fields:
  customized_paragraphs: >
    First paragraph
    multiline ok

    Second paragraph

  more: stuff
```

Get processed as `'First paragraph multiline ok\nSecond paragraph\n'`. You need to pass this through the `fix_newlines`
filter to have it rendered properly as two paragraphs, and it is also nice to pass it
through `wordwrap(120, False, None, False)` (use your own line width).

```jinja2
Some fixed paragraph

{{ customized_paragraphs | fix_newlines | wordwrap(120, False, None, False) }}

More paragraphs
```

## License

This project is [licensed under the EUPL](https://choosealicense.com/licenses/eupl-1.2/).
