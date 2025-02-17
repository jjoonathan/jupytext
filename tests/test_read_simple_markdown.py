from nbformat.v4.nbbase import new_code_cell, new_raw_cell, new_markdown_cell
from jupytext.compare import compare
import jupytext
from jupytext.combine import combine_inputs_with_outputs


def test_read_mostly_py_markdown_file(markdown="""---
title: Simple file
---

```python
import numpy as np
x = np.arange(0, 2*math.pi, eps)
```

```python
x = np.arange(0,1,eps)
y = np.abs(x)-.5
```

```
# this is a code cell with no language info
```

<!-- #raw -->
this is a raw cell
<!-- #endraw -->

```R
ls()
```

```R
cat(stringi::stri_rand_lipsum(3), sep='\n\n')
```
"""):
    nb = jupytext.reads(markdown, 'md')
    assert nb.metadata['jupytext']['main_language'] == 'python'
    compare(nb.cells, [{'cell_type': 'raw',
                        'source': '---\ntitle: Simple file\n---',
                        'metadata': {}},
                       {'cell_type': 'code',
                        'metadata': {},
                        'execution_count': None,
                        'source': 'import numpy as np\n'
                                  'x = np.arange(0, 2*math.pi, eps)',
                        'outputs': []},
                       {'cell_type': 'code',
                        'metadata': {},
                        'execution_count': None,
                        'source': 'x = np.arange(0,1,eps)\ny = np.abs(x)-.5',
                        'outputs': []},
                       {'cell_type': 'markdown',
                        'metadata': {},
                        'source': '```\n# this is a code cell with no language info\n```'},
                       {'cell_type': 'raw',
                        'metadata': {},
                        'source': 'this is a raw cell'},
                       {'cell_type': 'code',
                        'metadata': {},
                        'execution_count': None,
                        'source': '%%R\nls()',
                        'outputs': []},
                       {'cell_type': 'code',
                        'metadata': {},
                        'execution_count': None,
                        'source': "%%R\ncat(stringi::"
                                  "stri_rand_lipsum(3), sep='\n\n')",
                        'outputs': []}])

    markdown2 = jupytext.writes(nb, 'md')
    compare(markdown, markdown2)


def test_read_mostly_R_markdown_file(markdown="""```R
ls()
```

```R
cat(stringi::stri_rand_lipsum(3), sep='\n\n')
```
"""):
    nb = jupytext.reads(markdown, 'md')
    assert nb.metadata['jupytext']['main_language'] == 'R'
    compare(nb.cells, [{'cell_type': 'code',
                        'metadata': {},
                        'execution_count': None,
                        'source': 'ls()',
                        'outputs': []},
                       {'cell_type': 'code',
                        'metadata': {},
                        'execution_count': None,
                        'source': "cat(stringi::stri_rand_lipsum(3), sep='\n\n')",
                        'outputs': []}])

    markdown2 = jupytext.writes(nb, 'md')
    compare(markdown, markdown2)


def test_read_markdown_file_no_language(markdown="""```
ls
```

```
echo 'Hello World'
```
"""):
    nb = jupytext.reads(markdown, 'md')
    markdown2 = jupytext.writes(nb, 'md')
    compare(markdown, markdown2)


def test_read_julia_notebook(markdown="""```julia
1 + 1
```
"""):
    nb = jupytext.reads(markdown, 'md')
    assert nb.metadata['jupytext']['main_language'] == 'julia'
    assert len(nb.cells) == 1
    assert nb.cells[0].cell_type == 'code'
    markdown2 = jupytext.writes(nb, 'md')
    compare(markdown, markdown2)


def test_split_on_header(markdown="""A paragraph

# H1 Header

## H2 Header

Another paragraph
"""):
    fmt = {'extension': '.md', 'split_at_heading': True}
    nb = jupytext.reads(markdown, fmt)
    assert nb.cells[0].source == 'A paragraph'
    assert nb.cells[1].source == '# H1 Header'
    assert nb.cells[2].source == '## H2 Header\n\nAnother paragraph'
    assert len(nb.cells) == 3
    markdown2 = jupytext.writes(nb, fmt)
    compare(markdown, markdown2)


def test_split_on_header_after_two_blank_lines(markdown="""A paragraph


# H1 Header
"""):
    fmt = {'extension': '.Rmd', 'split_at_heading': True}
    nb = jupytext.reads(markdown, fmt)
    markdown2 = jupytext.writes(nb, fmt)
    compare(markdown, markdown2)


def test_code_cell_with_metadata(markdown="""```python tags=["parameters"]
a = 1
b = 2
```
"""):
    nb = jupytext.reads(markdown, 'md')
    compare(nb.cells[0], new_code_cell(source='a = 1\nb = 2', metadata={'tags': ['parameters']}))
    markdown2 = jupytext.writes(nb, 'md')
    compare(markdown, markdown2)


def test_raw_cell_with_metadata(markdown="""<!-- #raw {"key": "value"} -->
raw content
<!-- #endraw -->
"""):
    nb = jupytext.reads(markdown, 'md')
    compare(nb.cells[0], new_raw_cell(source='raw content', metadata={'key': 'value'}))
    markdown2 = jupytext.writes(nb, 'md')
    compare(markdown, markdown2)


def test_read_raw_cell_markdown_version_1_1(markdown="""---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.1'
      jupytext_version: 1.1.0
---

```key="value"
raw content
```
"""):
    nb = jupytext.reads(markdown, 'md')
    compare(nb.cells[0], new_raw_cell(source='raw content', metadata={'key': 'value'}))
    md2 = jupytext.writes(nb, 'md')
    assert "format_version: '1.1'" not in md2


def test_markdown_cell_with_metadata(markdown="""<!-- #region {"key": "value"} -->
A long


markdown cell
<!-- #endregion -->
"""):
    nb = jupytext.reads(markdown, 'md')
    compare(nb.cells[0], new_markdown_cell(source='A long\n\n\nmarkdown cell',
                                           metadata={'key': 'value'}))
    markdown2 = jupytext.writes(nb, 'md')
    compare(markdown, markdown2)


def test_two_markdown_cells(markdown="""# A header

<!-- #region -->
A long


markdown cell
<!-- #endregion -->
"""):
    nb = jupytext.reads(markdown, 'md')
    compare(nb.cells[0], new_markdown_cell(source='# A header'))
    compare(nb.cells[1], new_markdown_cell(source='A long\n\n\nmarkdown cell'))
    markdown2 = jupytext.writes(nb, 'md')
    compare(markdown, markdown2)


def test_combine_md_version_one():
    markdown = """---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.0'
      jupytext_version: 1.0.0
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

A short markdown cell

```
a raw cell
```

```python
1 + 1
```
"""
    # notebook read from markdown file in version 1.0
    nb_source = jupytext.reads(markdown, 'md')

    # actual notebook has metadata
    nb_meta = jupytext.reads(markdown, 'md')
    for cell in nb_meta.cells:
        cell.metadata = {'key': 'value'}

    combine_inputs_with_outputs(nb_source, nb_meta)
    for cell in nb_source.cells:
        assert cell.metadata == {'key': 'value'}, cell.source


def test_jupyter_cell_is_not_split():
    text = """Here we have a markdown
file with a jupyter code cell

```python
1 + 1


2 + 2
```

the code cell should become a Jupyter cell.
"""
    nb = jupytext.reads(text, 'md')
    assert nb.cells[0].cell_type == 'markdown'
    compare("""Here we have a markdown
file with a jupyter code cell""", nb.cells[0].source)

    assert nb.cells[1].cell_type == 'code'
    compare("""1 + 1


2 + 2""", nb.cells[1].source)

    assert nb.cells[2].cell_type == 'markdown'
    compare("the code cell should become a Jupyter cell.", nb.cells[2].source)
    assert len(nb.cells) == 3


def test_indented_code_is_not_split():
    text = """Here we have a markdown
file with an indented code cell

    1 + 1


    2 + 2

the code cell should not become a Jupyter cell,
nor be split into two pieces."""
    nb = jupytext.reads(text, 'md')
    compare(text, nb.cells[0].source)
    assert nb.cells[0].cell_type == 'markdown'
    assert len(nb.cells) == 1


def test_non_jupyter_code_is_not_split():
    text = """Here we have a markdown
file with a non-jupyter code cell

```{.python}
1 + 1


2 + 2
```

the code cell should not become a Jupyter cell,
nor be split into two pieces."""
    nb = jupytext.reads(text, 'md')
    compare(text, nb.cells[0].source)
    assert nb.cells[0].cell_type == 'markdown'
    assert len(nb.cells) == 1


def test_read_markdown_idl(no_jupytext_version_number, text='''---
jupyter:
  kernelspec:
    display_name: IDL [conda env:gdl] *
    language: IDL
    name: conda-env-gdl-idl
---

# A sample IDL Markdown notebook

```idl
a = 1
```
'''):
    nb = jupytext.reads(text, 'md')
    assert len(nb.cells) == 2
    assert nb.cells[1].cell_type == 'code'
    assert nb.cells[1].source == 'a = 1'

    text2 = jupytext.writes(nb, 'md')
    compare(text, text2)


def test_read_markdown_IDL(no_jupytext_version_number, text='''---
jupyter:
  kernelspec:
    display_name: IDL [conda env:gdl] *
    language: IDL
    name: conda-env-gdl-idl
---

# A sample IDL Markdown notebook

```IDL
a = 1
```
'''):
    nb = jupytext.reads(text, 'md')
    assert len(nb.cells) == 2
    assert nb.cells[1].cell_type == 'code'
    assert nb.cells[1].source == 'a = 1'

    text2 = jupytext.writes(nb, 'md')
    compare(text.replace('```IDL', '```idl'), text2)
