{% if not txt %}
<div id="main-body">
{% endif %}
{% filter md %}
Dear {{ first_name }},

I hereby present to you an awesome piece of software: **open-source mailmerge written in Python**.

It uses [Jinja2 templating][1], so you can use all kinds of fancy syntax to do introduce various logic. Most
importantly, a markdown filter is available (this block is wrapped in it), but you can also use conditional expressions
and blocks, for example to use a different signature for the plaintext and html versions of the mail.

[1]: https://jinja.palletsprojects.com/templates/

### Features

- lists
    - that support
    - sub items
- with clear separation of blocks
- styling customization soon

{% if not features %}
For example, you are seeing this, because no rich data was provided for you.
{% else %}
For example, specifically for you, we have chosen the following features to point-out and render using a for-cycle:

{% set keylen = ((features.keys() | list) + ["feature"]) | map('length') | max %}
{% set vallen = ((features.values() | list) + ["description"]) | map('length') | max %}
|{{ "feature" | center(keylen + 2) }}|{{ "description" | center(vallen + 2) }}|
|{{ "-"*(keylen + 2) }}|{{ "-" * (vallen + 2) }}|
{% for feature, description in features.items() %}
|{{ feature | center(keylen + 2) }}|{{ description | center(vallen + 2) }}|
{% endfor %}
{% endif %}

Anyways, that's it, I'll be happy to see you contribute your pull requests and report issues on Github.
{% endfilter %}
{% if not txt %}
</div>
{% endif %}


{% include "example-signature.txt" if txt else "example-signature.html" %}
