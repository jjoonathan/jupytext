import pytest
from nbformat.v4.nbbase import new_notebook, new_markdown_cell, new_code_cell, new_raw_cell
from jupytext.compare import compare
from jupytext.compare import compare_notebooks, NotebookDifference, test_round_trip_conversion as round_trip_conversion


def notebook_metadata():
    return {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.7.3"
        },
        "toc": {
            "base_numbering": 1,
            "nav_menu": {},
            "number_sections": True,
            "sideBar": True,
            "skip_h1_title": False,
            "title_cell": "Table of Contents",
            "title_sidebar": "Contents",
            "toc_cell": False,
            "toc_position": {},
            "toc_section_display": True,
            "toc_window_display": False
        }
    }


@pytest.fixture()
def notebook_1():
    return new_notebook(
        metadata=notebook_metadata(),
        cells=[new_markdown_cell('First markdown cell'),
               new_code_cell('1 + 1'),
               new_markdown_cell('Second markdown cell')])


@pytest.fixture()
def notebook_2():
    metadata = notebook_metadata()
    metadata['language_info']['version'] = '3.6.8'
    return new_notebook(
        metadata=metadata,
        cells=[new_markdown_cell('First markdown cell'),
               new_code_cell('1 + 1'),
               new_markdown_cell('Modified markdown cell')])


def test_compare_on_notebooks(notebook_1, notebook_2):
    with pytest.raises(AssertionError) as err:
        compare(notebook_1, notebook_2)

    assert str(err.value) == """
--- first
+++ second
@@ -15,7 +15,7 @@
   {
    "cell_type": "markdown",
    "metadata": {},
-   "source": "Second markdown cell"
+   "source": "Modified markdown cell"
   }
  ],
  "metadata": {
@@ -34,7 +34,7 @@
    "name": "python",
    "nbconvert_exporter": "python",
    "pygments_lexer": "ipython3",
-   "version": "3.7.3"
+   "version": "3.6.8"
   },
   "toc": {
    "base_numbering": 1,"""


def test_raise_on_different_metadata():
    ref = new_notebook(metadata={'kernelspec': {'language': 'python', 'name': 'python', 'display_name': 'Python'}},
                       cells=[new_markdown_cell('Cell one')])
    test = new_notebook(metadata={'kernelspec': {'language': 'R', 'name': 'R', 'display_name': 'R'}},
                        cells=[new_markdown_cell('Cell one')])
    with pytest.raises(NotebookDifference):
        compare_notebooks(ref, test, 'md')


@pytest.mark.parametrize('raise_on_first_difference', [True, False])
def test_raise_on_different_cell_type(raise_on_first_difference):
    ref = new_notebook(cells=[new_markdown_cell('Cell one'), new_code_cell('Cell two')])
    test = new_notebook(cells=[new_markdown_cell('Cell one'), new_raw_cell('Cell two')])
    with pytest.raises(NotebookDifference):
        compare_notebooks(ref, test, 'md', raise_on_first_difference=raise_on_first_difference)


@pytest.mark.parametrize('raise_on_first_difference', [True, False])
def test_raise_on_different_cell_content(raise_on_first_difference):
    ref = new_notebook(cells=[new_markdown_cell('Cell one'), new_code_cell('Cell two')])
    test = new_notebook(cells=[new_markdown_cell('Cell one'), new_code_cell('Modified cell two')])
    with pytest.raises(NotebookDifference):
        compare_notebooks(ref, test, 'md', raise_on_first_difference=raise_on_first_difference)


def test_raise_on_incomplete_markdown_cell():
    ref = new_notebook(cells=[new_markdown_cell('Cell one\n\n\nsecond line')])
    test = new_notebook(cells=[new_markdown_cell('Cell one')])
    with pytest.raises(NotebookDifference):
        compare_notebooks(ref, test, 'md')


def test_does_raise_on_split_markdown_cell():
    ref = new_notebook(cells=[new_markdown_cell('Cell one\n\n\nsecond line')])
    test = new_notebook(cells=[new_markdown_cell('Cell one'),
                               new_markdown_cell('second line')])
    with pytest.raises(NotebookDifference):
        compare_notebooks(ref, test, 'md')


def test_raise_on_different_cell_metadata():
    ref = new_notebook(cells=[new_code_cell('1+1')])
    test = new_notebook(cells=[new_code_cell('1+1', metadata={'metakey': 'value'})])
    with pytest.raises(NotebookDifference):
        compare_notebooks(ref, test, 'py:light')


@pytest.mark.parametrize('raise_on_first_difference', [True, False])
def test_raise_on_different_cell_count(raise_on_first_difference):
    ref = new_notebook(cells=[new_code_cell('1')])
    test = new_notebook(cells=[new_code_cell('1'),
                               new_code_cell('2')])
    with pytest.raises(NotebookDifference):
        compare_notebooks(ref, test, 'py:light', raise_on_first_difference=raise_on_first_difference)

    with pytest.raises(NotebookDifference):
        compare_notebooks(test, ref, 'py:light', raise_on_first_difference=raise_on_first_difference)


def test_does_not_raise_on_blank_line_removed():
    ref = new_notebook(cells=[new_code_cell('1+1\n    ')])
    test = new_notebook(cells=[new_code_cell('1+1')])
    compare_notebooks(ref, test, 'py:light')


def test_strict_raise_on_blank_line_removed():
    ref = new_notebook(cells=[new_code_cell('1+1\n')])
    test = new_notebook(cells=[new_code_cell('1+1')])
    with pytest.raises(NotebookDifference):
        compare_notebooks(ref, test, 'py:light', allow_expected_differences=False)


def test_dont_raise_on_different_outputs():
    ref = new_notebook(cells=[new_code_cell('1+1')])
    test = new_notebook(cells=[new_code_cell('1+1', outputs=[
        {
            "data": {
                "text/plain": [
                    "2"
                ]
            },
            "execution_count": 1,
            "metadata": {},
            "output_type": "execute_result"
        }
    ])])
    compare_notebooks(ref, test, 'md')


@pytest.mark.parametrize('raise_on_first_difference', [True, False])
def test_raise_on_different_outputs(raise_on_first_difference):
    ref = new_notebook(cells=[new_code_cell('1+1')])
    test = new_notebook(cells=[new_code_cell('1+1', outputs=[
        {
            "data": {
                "text/plain": [
                    "2"
                ]
            },
            "execution_count": 1,
            "metadata": {},
            "output_type": "execute_result"
        }
    ])])
    with pytest.raises(NotebookDifference):
        compare_notebooks(ref, test, 'md', compare_outputs=True, raise_on_first_difference=raise_on_first_difference)


def test_test_round_trip_conversion():
    notebook = new_notebook(cells=[new_code_cell('1+1', outputs=[
        {
            "data": {
                "text/plain": [
                    "2"
                ]
            },
            "execution_count": 1,
            "metadata": {},
            "output_type": "execute_result"
        }
    ])], metadata={'main_language': 'python'})

    round_trip_conversion(notebook, {'extension': '.py'}, update=True)


def test_mutiple_cells_differ():
    nb1 = new_notebook(cells=[new_code_cell(''),
                              new_code_cell('2')])
    nb2 = new_notebook(cells=[new_code_cell('1+1'),
                              new_code_cell('2\n2')])
    with pytest.raises(NotebookDifference) as exception_info:
        compare_notebooks(nb1, nb2, raise_on_first_difference=False)
    assert 'Cells 1,2 differ' in exception_info.value.args[0]


def test_cell_metadata_differ():
    nb1 = new_notebook(cells=[new_code_cell('1'),
                              new_code_cell('2', metadata={'additional': 'metadata1'})])
    nb2 = new_notebook(cells=[new_code_cell('1'),
                              new_code_cell('2', metadata={'additional': 'metadata2'})])
    with pytest.raises(NotebookDifference) as exception_info:
        compare_notebooks(nb1, nb2, raise_on_first_difference=False)
    assert "Cell metadata 'additional' differ" in exception_info.value.args[0]


def test_notebook_metadata_differ():
    nb1 = new_notebook(cells=[new_code_cell('1'),
                              new_code_cell('2')])
    nb2 = new_notebook(cells=[new_code_cell('1'),
                              new_code_cell('2')],
                       metadata={'kernelspec': {'language': 'python', 'name': 'python', 'display_name': 'Python'}})
    with pytest.raises(NotebookDifference) as exception_info:
        compare_notebooks(nb1, nb2, raise_on_first_difference=False, )
    assert "Notebook metadata differ" in exception_info.value.args[0]
