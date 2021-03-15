{% if not txt %}
<style>
    #mailmerge-main-body > p {
        margin-bottom: 1em;
    }
</style>
<div id="mailmerge-main-body">
{% endif %}
{% filter md %}
Dear {{ first_name }},

I hereby present to you an awesome piece of software: **open-source mailmerge written in Python**.

It uses [Jinja2 templating][1], so you can use all kinds of fancy syntax to do introduce various logic. Most
importantly, a markdown filter is available (this block is wrapped in it), but you can also use conditional expressions
and blocks, for example to use a different signature for the plaintext and html versions of the mail.

[1]: https://jinja.palletsprojects.com/templates/

For-cycles are also available, {% if not features %}but unfortunately we couldn't show off because the needed data
weren't provided for you.{% else %}so specifically for you, we have chosen the following set of features to point-out,
which were rendered using a for-cycle:

|feature|description|
|--|--|
{% for feature, description in features.items() %}
|{{ feature }}|{{ description }}|
{% endfor %}{% endif %}

Anyways, that's it, I'll be happy to see you contribute your pull requests and report issues on Github.
{% endfilter %}
{% if not txt %}
</div>
{% endif %}


{% include "example-signature.txt" if txt else "example-signature.html" %}
