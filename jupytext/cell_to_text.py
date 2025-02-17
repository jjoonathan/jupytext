"""Export notebook cells as text"""

import re
import json
import warnings
from copy import copy
from .languages import cell_language, comment_lines
from .cell_metadata import is_active, _IGNORE_CELL_METADATA
from .cell_metadata import metadata_to_md_options, metadata_to_rmd_options
from .cell_metadata import metadata_to_json_options, metadata_to_double_percent_options
from .metadata_filter import filter_metadata
from .magics import comment_magic, escape_code_start
from .cell_reader import LightScriptCellReader, MarkdownCellReader, RMarkdownCellReader
from .languages import _SCRIPT_EXTENSIONS
from .pep8 import pep8_lines_between_cells


def cell_source(cell):
    """Return the source of the current cell, as an array of lines"""
    source = cell.source
    if source == '':
        return ['']
    if source.endswith('\n'):
        return source.splitlines() + ['']
    return source.splitlines()


class BaseCellExporter(object):
    """A class that represent a notebook cell as text"""
    default_comment_magics = None
    parse_cell_language = True

    def __init__(self, cell, default_language, fmt=None):
        self.fmt = fmt or {}
        self.ext = self.fmt.get('extension')
        self.cell_type = cell.cell_type
        self.source = cell_source(cell)
        self.unfiltered_metadata = cell.metadata
        self.metadata = filter_metadata(copy(cell.metadata),
                                        self.fmt.get('cell_metadata_filter'),
                                        _IGNORE_CELL_METADATA)
        self.language, magic_args = cell_language(self.source) if self.parse_cell_language else (None, None)

        if self.language:
            if magic_args:
                if self.ext.endswith('.Rmd'):
                    quote = '"' if "'" in magic_args else "'"
                    magic_args = quote + magic_args + quote
                self.metadata['magic_args'] = magic_args

            if not self.ext.endswith('.Rmd'):
                self.metadata['language'] = self.language

        self.language = self.language or default_language
        self.default_language = default_language
        self.comment = _SCRIPT_EXTENSIONS.get(self.ext, {}).get('comment', '#')
        self.comment_magics = self.fmt['comment_magics'] if 'comment_magics' in self.fmt \
            else self.default_comment_magics

        # how many blank lines before next cell
        self.lines_to_next_cell = cell.metadata.get('lines_to_next_cell')
        self.lines_to_end_of_cell_marker = cell.metadata.get('lines_to_end_of_cell_marker')

        if cell.cell_type == 'raw' and 'active' not in self.metadata:
            self.metadata['active'] = ''

    def is_code(self):
        """Is this cell a code cell?"""
        if self.cell_type == 'code':
            return True
        if self.cell_type == 'raw' and 'active' in self.metadata:
            return True
        return False

    def cell_to_text(self):
        """Return the text representation for the cell"""
        if self.is_code():
            return self.code_to_text()

        source = copy(self.source)
        if not self.comment:
            escape_code_start(source, self.ext, None)
        return self.markdown_to_text(source)

    def markdown_to_text(self, source):
        """Escape the given source, for a markdown cell"""
        if self.comment and self.comment != "#'":
            source = copy(source)
            comment_magic(source, self.language, self.comment_magics)

        return comment_lines(source, self.comment)

    def code_to_text(self):
        """Return the text representation of this cell as a code cell"""
        raise NotImplementedError('This method must be implemented in a sub-class')

    def remove_eoc_marker(self, text, next_text):
        """Remove end-of-cell marker when possible"""
        # pylint: disable=W0613,R0201
        return text

    def simplify_soc_marker(self, text, prev_text):
        """Simplify start-of-cell marker when possible"""
        # pylint: disable=W0613,R0201
        return text


class MarkdownCellExporter(BaseCellExporter):
    """A class that represent a notebook cell as Markdown"""
    default_comment_magics = False
    cell_reader = MarkdownCellReader

    def __init__(self, *args, **kwargs):
        BaseCellExporter.__init__(self, *args, **kwargs)
        self.comment = ''

    def html_comment(self, metadata, code='region'):
        """Encore the source text in an HTML region"""
        if metadata:
            region_start = ['<!-- #' + code]
            if 'title' in metadata and '{' not in metadata['title']:
                region_start.append(metadata.pop('title'))
            region_start.append(json.dumps(metadata))
            region_start.append('-->')
            region_start = ' '.join(region_start)
        else:
            region_start = '<!-- #{} -->'.format(code)

        return [region_start] + self.source + ['<!-- #end{} -->'.format(code)]

    def cell_to_text(self):
        """Return the text representation of a cell"""
        if self.cell_type == 'markdown':
            # Is an explicit region required?
            if self.metadata or self.cell_reader(self.fmt).read(self.source)[1] < len(self.source):
                return self.html_comment(self.metadata)
            return self.source

        return self.code_to_text()

    def code_to_text(self):
        """Return the text representation of a code cell"""
        source = copy(self.source)
        comment_magic(source, self.language, self.comment_magics)

        options = []
        if self.cell_type == 'code' and self.language:
            options.append(self.language)

        filtered_metadata = {key: self.metadata[key] for key in self.metadata
                             if key not in ['active', 'language']}

        if filtered_metadata:
            options.append(metadata_to_md_options(filtered_metadata))

        if self.cell_type == 'raw':
            return self.html_comment(filtered_metadata, 'raw')

        return ['```{}'.format(' '.join(options))] + source + ['```']


class RMarkdownCellExporter(MarkdownCellExporter):
    """A class that represent a notebook cell as R Markdown"""
    default_comment_magics = True
    cell_reader = RMarkdownCellReader

    def __init__(self, *args, **kwargs):
        MarkdownCellExporter.__init__(self, *args, **kwargs)
        self.ext = '.Rmd'
        self.comment = ''

    def code_to_text(self):
        """Return the text representation of a code cell"""
        active = is_active(self.ext, self.metadata)
        source = copy(self.source)

        if active:
            comment_magic(source, self.language, self.comment_magics)

        lines = []
        if not is_active('Rmd', self.metadata):
            self.metadata['eval'] = False
        options = metadata_to_rmd_options(self.language, self.metadata)
        lines.append('```{{{}}}'.format(options))
        lines.extend(source)
        lines.append('```')
        return lines


def endofcell_marker(source, comment):
    """Issues #31 #38:  does the cell contain a blank line? In that case
    we add an end-of-cell marker"""
    endofcell = '-'
    while True:
        endofcell_re = re.compile(r'^{}( )'.format(comment) + endofcell + r'\s*$')
        if list(filter(endofcell_re.match, source)):
            endofcell = endofcell + '-'
        else:
            return endofcell


class LightScriptCellExporter(BaseCellExporter):
    """A class that represent a notebook cell as a Python or Julia script"""
    default_comment_magics = True
    use_cell_markers = True
    cell_marker_start = None
    cell_marker_end = None

    def __init__(self, *args, **kwargs):
        BaseCellExporter.__init__(self, *args, **kwargs)
        if 'cell_markers' in self.fmt:
            if ',' not in self.fmt['cell_markers']:
                warnings.warn("Ignored cell markers '{}' as it does not match the expected 'start,end' pattern"
                              .format(self.fmt.pop('cell_markers')))
            elif self.fmt['cell_markers'] != '+,-':
                self.cell_marker_start, self.cell_marker_end = self.fmt['cell_markers'].split(',', 1)
        for key in ['endofcell']:
            if key in self.unfiltered_metadata:
                self.metadata[key] = self.unfiltered_metadata[key]

    def is_code(self):
        # Treat markdown cells with metadata as code cells (#66)
        if self.cell_type == 'markdown' and self.metadata:
            self.metadata['cell_type'] = self.cell_type
            self.source = comment_lines(self.source, self.comment)
            return True
        return super(LightScriptCellExporter, self).is_code()

    def code_to_text(self):
        """Return the text representation of a code cell"""
        active = is_active(self.ext, self.metadata)
        if self.language != self.default_language and 'active' not in self.metadata:
            active = False

        source = copy(self.source)
        escape_code_start(source, self.ext, self.language)

        if active:
            comment_magic(source, self.language, self.comment_magics)
        else:
            source = [self.comment + ' ' + line if line else self.comment for line in source]

        if self.explicit_start_marker(source):
            self.metadata['endofcell'] = self.cell_marker_end or endofcell_marker(source, self.comment)

        if not self.metadata or not self.use_cell_markers:
            return source

        lines = []
        endofcell = self.metadata['endofcell']
        if endofcell == '-' or self.cell_marker_end:
            del self.metadata['endofcell']

        cell_start = [self.comment, self.cell_marker_start or '+']
        if not self.cell_marker_start:
            cell_start.append(metadata_to_json_options(self.metadata))
        elif self.metadata:
            if 'title' in self.metadata:
                cell_start.append(self.metadata.pop('title'))
            if self.metadata:
                cell_start.append(metadata_to_json_options(self.metadata))

        lines.append(' '.join(cell_start))
        lines.extend(source)
        lines.append(self.comment + ' {}'.format(endofcell))
        return lines

    def explicit_start_marker(self, source):
        """Does the python representation of this cell requires an explicit
        start of cell marker?"""
        if not self.use_cell_markers:
            return False
        if self.metadata:
            return True
        if self.cell_marker_start:
            start_code_re = re.compile('^' + self.comment + r'\s*' + self.cell_marker_start + r'\s*(.*)$')
            end_code_re = re.compile('^' + self.comment + r'\s*' + self.cell_marker_end + r'\s*$')
            if start_code_re.match(source[0]) or end_code_re.match(source[0]):
                return False

        if all([line.startswith(self.comment) for line in self.source]):
            return True
        if LightScriptCellReader(self.fmt).read(source)[1] < len(source):
            return True

        return False

    def remove_eoc_marker(self, text, next_text):
        """Remove end of cell marker when next cell has an explicit start marker"""
        if self.cell_marker_start:
            return text

        if self.is_code() and text[-1] == self.comment + ' -':
            # remove end of cell marker when redundant with next explicit marker
            if not next_text or next_text[0].startswith(self.comment + ' + {'):
                text = text[:-1]
                # When we do not need the end of cell marker, number of blank lines is the max
                # between that required at the end of the cell, and that required before the next cell.
                if self.lines_to_end_of_cell_marker and (self.lines_to_next_cell is None or
                                                         self.lines_to_end_of_cell_marker > self.lines_to_next_cell):
                    self.lines_to_next_cell = self.lines_to_end_of_cell_marker
            else:
                # Insert blank lines at the end of the cell
                blank_lines = self.lines_to_end_of_cell_marker
                if blank_lines is None:
                    # two blank lines when required by pep8
                    blank_lines = pep8_lines_between_cells(text[:-1], next_text, self.ext)
                    blank_lines = 0 if blank_lines < 2 else 2
                text = text[:-1] + [''] * blank_lines + text[-1:]

        return text

    def simplify_soc_marker(self, text, prev_text):
        """Simplify start of cell marker when previous line is blank"""
        if self.cell_marker_start:
            return text

        if self.is_code() and text and text[0] == self.comment + ' + {}':
            if not prev_text or not prev_text[-1].strip():
                text[0] = self.comment + ' +'

        return text


class BareScriptCellExporter(LightScriptCellExporter):
    """A class that writes notebook cells as scripts with no cell markers"""
    use_cell_markers = False


class RScriptCellExporter(BaseCellExporter):
    """A class that can represent a notebook cell as a R script"""
    default_comment_magics = True

    def __init__(self, *args, **kwargs):
        BaseCellExporter.__init__(self, *args, **kwargs)
        self.comment = "#'"

    def code_to_text(self):
        """Return the text representation of a code cell"""
        active = is_active(self.ext, self.metadata)
        source = copy(self.source)
        escape_code_start(source, self.ext, self.language)

        if active:
            comment_magic(source, self.language, self.comment_magics)

        if not active:
            source = ['# ' + line if line else '#' for line in source]

        lines = []
        if not is_active('R', self.metadata):
            self.metadata['eval'] = False
        options = metadata_to_rmd_options(None, self.metadata)
        if options:
            lines.append('#+ {}'.format(options))
        lines.extend(source)
        return lines


class DoublePercentCellExporter(BaseCellExporter):  # pylint: disable=W0223
    """A class that can represent a notebook cell as a Spyder/VScode script (#59)"""
    default_comment_magics = True
    parse_cell_language = True

    def __init__(self, *args, **kwargs):
        BaseCellExporter.__init__(self, *args, **kwargs)
        self.cell_markers = self.fmt.get('cell_markers')

    def cell_to_text(self):
        """Return the text representation for the cell"""
        if self.cell_type != 'code':
            self.metadata['cell_type'] = self.cell_type

        active = is_active('py', self.metadata)
        if self.language != self.default_language and 'active' not in self.metadata:
            active = False
        if self.cell_type == 'raw' and 'active' in self.metadata and self.metadata['active'] == '':
            del self.metadata['active']

        options = metadata_to_double_percent_options(self.metadata)
        if options.startswith('%') or not options:
            lines = [self.comment + ' %%' + options]
        else:
            lines = [self.comment + ' %% ' + options]

        if self.cell_type == 'code' and active:
            source = copy(self.source)
            comment_magic(source, self.language, self.comment_magics)
            if source == ['']:
                return lines
            return lines + source

        cell_marker = self.unfiltered_metadata.get('cell_marker', self.cell_markers)
        if self.cell_type != 'code' and cell_marker:
            return lines + [cell_marker] + self.source + [cell_marker]

        return lines + comment_lines(self.source, self.comment)


class HydrogenCellExporter(DoublePercentCellExporter):  # pylint: disable=W0223
    """A class that can represent a notebook cell as a Hydrogen script (#59)"""
    default_comment_magics = False
    parse_cell_language = False


class SphinxGalleryCellExporter(BaseCellExporter):  # pylint: disable=W0223
    """A class that can represent a notebook cell as a
    Sphinx Gallery script (#80)"""

    default_cell_marker = '#' * 79
    default_comment_magics = True

    def __init__(self, *args, **kwargs):
        BaseCellExporter.__init__(self, *args, **kwargs)
        self.comment = '#'

        for key in ['cell_marker']:
            if key in self.unfiltered_metadata:
                self.metadata[key] = self.unfiltered_metadata[key]

        if self.fmt.get('rst2md'):
            raise ValueError("The 'rst2md' option is a read only option. The reverse conversion is not "
                             "implemented. Please either deactivate the option, or save to another format.")

    def cell_to_text(self):
        """Return the text representation for the cell"""
        if self.cell_type == 'code':
            source = copy(self.source)
            return comment_magic(source, self.language, self.comment_magics)

        if 'cell_marker' in self.metadata:
            cell_marker = self.metadata.pop('cell_marker')
        else:
            cell_marker = self.default_cell_marker

        if self.source == ['']:
            return [cell_marker] if cell_marker in ['""', "''"] else ['""']

        if cell_marker in ['"""', "'''"]:
            return [cell_marker] + self.source + [cell_marker]

        return [cell_marker if cell_marker.startswith('#' * 20)
                else self.default_cell_marker] + comment_lines(self.source, self.comment)
