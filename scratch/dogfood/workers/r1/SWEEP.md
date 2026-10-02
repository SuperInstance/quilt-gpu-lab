# (A) BUG candidates: unary +/-/! or Number()/parseInt()/parseFloat() applied
#     directly to an operand, then ??  — no parens around the coercion.
rg -n --pcre2 '(?<![()\w])(?:[+\-!]\s*[\w.$\[\]"'"'"']+\s*\)|\b(?:Number|parseInt|parseFloat)\s*\([^()\n]*\))\s*\?\?' \
    -g '*.js' -g '*.mjs' -g '*.ts' ROOT

# (B) SANE control: coercion wrapped in parens before ??
rg -n --pcre2 '\(\s*(?:[+\-!]?\s*[\w.$\[\]"'"'"']+|\b(?:Number|parseInt|parseFloat)\s*\([^()\n]*\))\s*\)\s*\?\?' \
    -g '*.js' -g '*.mjs' -g '*.ts' ROOT
