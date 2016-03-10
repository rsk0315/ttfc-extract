#!/usr/bin/env python

import datetime
import struct
from StringIO import StringIO

from name_table import *


# Reference:
# https://developer.apple.com/fonts/TrueType-Reference-Manual/

_version = '0.1.1'

class TTFObject(object):
    def __init__(self, fin):
        self.fin = fin
        self.fin.seek(0)

        self.sfnt_version = fixed(self.fin.read(4))
        (
            self.num_of_tables,
            self.search_range,      # (max power of 2 <= num_of_tables) * 16
            self.entry_selector,    # (log[2](max power of 2 <= num_of_tables)
            self.range_shift,       # num_of_tables * 16 - search_range
        ) = struct.unpack('>4H', self.fin.read(8))

        self.tables = {}
        for i in range(self.num_of_tables):
            (
                table_name, checksum, offset, length
            ) = struct.unpack('>4s3I', self.fin.read(0x10))

            self.tables[table_name] = TTFTable(checksum, offset, length)

    def save(
            self, index,
            outname='{index}-{gname}.svg',
            scale=1.0,
    ):
        'variables:\n'
        '  {index} - glyph index\n'
        '  {gname} - glyph name\n'
        '  {fname} - font name\n'  # TODO
        'you can use python-style format\n'
        'e.g. "0x{name:0>2x}-{name}.svg"'
        name = self.post.names[index]

        x_min = self.head.x_min
        x_max = self.head.x_max
        y_min = self.head.y_min
        y_max = self.head.y_max

        if self.glyf.glyphs[index] is None:
            string = '<svg/>'

        else:
            string = (
                '<svg\n'
                '    width="{x}"\n'
                '    height="{y}"\n'
                '    viewBox="{offset_x} {offset_y} {x} {y}"\n'
                '    xmlns="http://www.w3.org/2000/svg"\n'
                '>\n'.format(
                    x=scale*(x_max-x_min+1),
                    y=scale*(y_max-y_min+1),
                    # offset=-2048*scale,
                    offset_x=scale*x_min,
                    offset_y=scale*(-y_max),
                )
            )
            string += self.glyf.draw_line(index, scale=scale)
            string += '</svg>'

        for i, nr in enumerate(self.name.name_record_array):
            if (
                nr.platform_id,
                nr.specific_id,
                nr.language_id,
                nr.name_id,
            ) == (1, 0, 0, 6):
                fname = self.name.get_string(i)
                break
        else:
            fname = ''

        outname = outname.format(
            index=index,
            name=name,
            fname=fname,
        )
        with open(outname, 'w') as fout:
            fout.write(string)

        return outname


class TTFTable(object):
    def __init__(self, checksum, offset, length):
        self.checksum = checksum
        self.offset = offset
        self.length = length


class TTFHead(object):
    def __init__(self, ttf):
        ttf.fin.seek(ttf.tables['head'].offset)

        self.version = fixed(ttf.fin.read(4))
        self.font_revision = fixed(ttf.fin.read(4))
        (
            self.check_sum_adjustment,
            self.magic_number,
        ) = struct.unpack('>2I', ttf.fin.read(8))
        # 0x0001 - baseline(y)=0
        # 0x0002 - lsb(x)=0
        # 0x0004 - optical scl
        # 0x0008 - int ppem
        # 0x0010 - nonlin aw
        (
            self.flags,
            self.units_per_em,
        ) = struct.unpack('>2H', ttf.fin.read(4))
        self.created = long_date_time(ttf.fin.read(8))
        self.modified = long_date_time(ttf.fin.read(8))
        (
            self.x_min, self.y_min,
            self.x_max, self.y_max,
            self.mac_style,
            self.lowest_rec_ppem,
            self.font_direction_hint,
            self.index_to_loc_format,
            self.glyph_data_format,
        ) = struct.unpack('>4h2H3h', ttf.fin.read(0x12))


class TTFHHea(object):
    def __init__(self, ttf):
        ttf.fin.seek(ttf.tables['hhea'].offset)
        self.version = fixed(ttf.fin.read(4))
        (
            self.ascent,
            self.descent,
            self.line_gap,
            self.advance_width_max,
            self.min_left_side_bearing,
            self.min_right_side_bearing,
            self.x_max_extent,
            self.caret_slope_rise,
            self.caret_slope_run,
            self.caret_offset,
        ) = struct.unpack('>3hH6h', ttf.fin.read(0x14))
        self.reserved = struct.unpack('>4h', ttf.fin.read(8))
        (
            self.metric_data_format,
            self.num_of_long_hor_metrics,
        ) = struct.unpack('>hH', ttf.fin.read(0x4))


class TTFMaxP(object):
    def __init__(self, ttf):
        ttf.fin.seek(ttf.tables['maxp'].offset)
        self.version = fixed(ttf.fin.read(4))
        (
            self.num_glyphs,
            self.max_points,
            self.max_contours,
            self.max_composite_points,
            self.max_composite_contours,
            self.max_zones,
            self.max_twilight_points,
            self.max_storage,
            self.max_function_defs,
            self.max_instruction_defs,
            self.max_stack_elements,
            self.max_size_of_instructions,
            self.max_component_elements,
            self.max_component_depth,
        ) = struct.unpack('>14H', ttf.fin.read(0x1c))


class TTFName(object):
    def __init__(self, ttf):
        ttf.fin.seek(ttf.tables['name'].offset)
        (
            self.format,
            self.count,
            self.string_offset,
        ) = struct.unpack('>3H', ttf.fin.read(6))

        self.name_record_array = []
        for i in range(self.count):
            name_record = TTFNameRecord(ttf.fin.read(0xc))
            self.name_record_array.append(name_record)

        string_length = ttf.tables['name'].length - self.string_offset
        self.string = StringIO(ttf.fin.read(string_length))

    def get_string(self, index):
        if not index < self.count:
            return ''

        self.string.seek(self.name_record_array[index].offset)
        string = self.string.read(self.name_record_array[index].length)
        return string  #.encode('some_encoding')

class TTFNameRecord(object):
    def __init__(self, stream):
        (
            self.platform_id,
            self.specific_id,
            self.language_id,
            self.name_id,
            self.length,
            self.offset,
        ) = struct.unpack('>6H', stream)


class TTFOS_2(object):
    def __init__(self, ttf):
        ttf.fin.seek(ttf.tables['OS/2'].offset)
        (
            self.version,
            self.x_avg_char_width,
            self.us_weight_class,
            self.us_width_class,
            self.fs_type,
            self.y_subscript_x_size,
            self.y_subscript_y_size,
            self.y_subscript_x_offset,
            self.y_subscript_y_offset,
            self.y_superscript_x_size,
            self.y_superscript_y_size,
            self.y_superscript_x_offset,
            self.y_superscript_y_offset,
            self.y_strikeout_size,
            self.y_strikeout_position,
            self.s_family_class,
        ) = struct.unpack('>Hh2H12h', ttf.fin.read(0x20))
        self.panose = struct.unpack('>10B', ttf.fin.read(0xa))
        self.unicode_range = struct.unpack('>4I', ttf.fin.read(0x10))
        self.ach_vend_id = ttf.fin.read(4)
        (
            self.fs_selection,
            self.fs_first_char_index,
            self.fs_last_char_index,
            self.s_typo_ascender,
            self.s_typo_descender,
            self.s_typo_linegap,
            self.us_win_ascent,
            self.us_win_descent,
        ) = struct.unpack('>3H3h2H', ttf.fin.read(0x10))
        self.code_page_range = struct.unpack('>2I', ttf.fin.read(8))
        (
            self.sx_height,
            self.s_cap_height,
            self.us_default_char,
            self.us_break_char,
            self.us_max_context,
        ) = struct.unpack('>2h3H', ttf.fin.read(0xa))
        if self.version >= 5.0:
            (
                self.us_lower_point_size,
                self.us_upper_point_size,
            ) = struct.unpack('>2H', ttf.fin.read(4))


class TTFPost(object):
    def __init__(self, ttf):
        ttf.fin.seek(ttf.tables['post'].offset)

        self.version = fixed(ttf.fin.read(4))
        self.italic_angle = fixed(ttf.fin.read(4))
        (
            self.underline_position,
            self.underline_thickness,
            self.is_fixed_pitch,
            self.min_mem_type_42,
            self.max_mem_type_42,
            self.min_mem_type_1,
            self.max_mem_type_1,
        ) = struct.unpack('>2h5I', ttf.fin.read(0x18))

        self.number_of_glyphs, = struct.unpack('>H', ttf.fin.read(2))
        if not self.number_of_glyphs == ttf.maxp.num_glyphs:
            raise ValueError

        self.glyph_name_indices = []
        self.number_new_glyphs = 0

        for i in range(self.number_of_glyphs):
            index, = struct.unpack('>H', ttf.fin.read(2))
            self.glyph_name_indices.append(index)
            if index > 257:
                self.number_new_glyphs += 1

        if self.version == 1.0:
            pass
        elif self.version == 2.0:
            ps_glyphs = []
            for i in range(self.number_new_glyphs):
                name = pascal_string(ttf.fin)
                ps_glyphs.append(name)

            self.names = []
            for index in self.glyph_name_indices:
                if index < 258:
                    self.names.append(MAC_GLYPHS[index])
                else:
                    self.names.append(ps_glyphs[index-258])

        elif self.version == 2.5:
            pass
        elif self.version == 3.0:
            pass
        elif self.version == 4.0:
            pass


class TTFCMap(object):
    def __init__(self, ttf):
        ttf.fin.seek(ttf.tables['cmap'].offset)
        length = ttf.tables['cmap'].length
        self.fin = StringIO(ttf.fin.read(length))
        (
            self.version,
            self.number_subtables,
        ) = struct.unpack('>2H', self.fin.read(4))

        self.subtables = []
        for i in range(self.number_subtables):
            subtable = TTFCMapSubtable(self.fin)
            self.subtables.append(subtable)

        for subtable in self.subtables:
            subtable.get_data()

class TTFCMapSubtable(object):
    def __init__(self, fin):
        self.fin = fin
        (
            self.platform_id,
            self.platform_specific_id,
            self.offset,
        ) = struct.unpack('>2HI', self.fin.read(8))

    def get_data(self):
        self.fin.seek(self.offset)
        self.format, = struct.unpack('>H', self.fin.read(2))
        if self.format == 0:
            (
                self.length,
                self.language,
            ) = struct.unpack('>2H', self.fin.read(4))
            self.glyph_index_array = []
            for i in range(256):
                glyph_index, = struct.unpack('>B', self.fin.read(2))
                self.glyph_index_array.append(glyph_index)

        elif self.format == 2:
            pass
        elif self.format == 4:
            pass
        elif self.format == 6:
            pass
        elif self.format == 8.0:  # in Fixed32
            pass
        elif self.format == 10.0:
            pass
        elif self.format == 12.0:
            pass
        elif self.format == 13.0:
            pass
        elif self.format == 14:
            pass
        else:
            pass


class TTFHMtx(object):
    def __init__(self, ttf):
        ttf.fin.seek(ttf.tables['hmtx'].offset)

        self.h_metrics = []
        for i in range(ttf.hhea.num_of_long_hor_metrics):
            long_hor_metric = TTFHMtxHMetric(ttf.fin.read(4))
            self.h_metrics.append(long_hor_metric)

class TTFHMtxHMetric(object):
    def __init__(self, stream):
        (
            self.advance_width,
            self.left_side_bearing,
        ) = struct.unpack('>Hh', stream)


class TTFLoca(object):
    def __init__(self, ttf):
        ttf.fin.seek(ttf.tables['loca'].offset)

        num_glyphs = ttf.maxp.num_glyphs
        index_to_loc_format = ttf.head.index_to_loc_format

        self.offsets = []
        if index_to_loc_format == 0:
            for i in range(num_glyphs+1):
                offset = 2 * struct.unpack('>H', ttf.fin.read(2))[0]
                self.offsets.append(offset)

        elif index_of_loc_format == 1:
            for i in range(num_glyphs+1):
                offset, = struct.unpack('>I', ttf.fin.read(4))
                self.offsets.append(offset)


class TTFGlyf(object):
    def __init__(self, ttf):
        ttf.fin.seek(ttf.tables['glyf'].offset)
        offsets = ttf.loca.offsets

        self.glyphs = []
        for i, offset in enumerate(offsets[:-1]):
            length = offsets[i+1] - offset
            stream = StringIO(ttf.fin.read(length))
            if length:
                glyph = TTFGlyfGlyph(stream)
                self.glyphs.append(glyph)
            else:
                self.glyphs.append(None)

    def draw_line(
            self, index,
            matrix=[[1.0, 0.0], [0.0, 1.0]],
            offset=[0.0, 0.0],
            scale=0.5,
    ):
        if not index < len(self.glyphs):
            return ''

        if self.glyphs[index] is None:
            return ''

        (a, b), (c, d) = matrix

        glyph = self.glyphs[index]
        if glyph.glyph_type == 'composite':
            string = ''
            for component in glyph.components:
                c_index = component.glyph_index
                z, w = component.arg1, component.arg2  # XXX
                z, w = [
                    a*z + b*w,
                    c*z + d*w,
                ]
                (s, t), (u, v) = component.matrix
                mat = [
                    [a*s + b*u, a*t + b*v],
                    [c*s + d*u, c*t + d*v],
                ]
                string += self.draw_line(
                    c_index,
                    matrix=mat,
                    offset=[z, -w],
                    scale=scale,
                ) + '\n'


        elif glyph.glyph_type == 'simple':
            contours = [[[], []]]
            a, b, c, d = [scale * i for i in (a, b, c, d)]
            x, y = offset
            x, y = [
                a*x + b*y,
                c*x + d*y,
            ]
            for index, (flag, coordinate), in enumerate(
                zip(glyph.flags, glyph.coordinates)
            ):
                contours[-1][0].append(flag)

                dx, dy = coordinate
                x += (a * dx) + (b * dy)
                y -= (c * dx) + (d * dy)
                contours[-1][1].append((x, y))

                if glyph.end_pts_of_contours[len(contours)-1] == index:
                    contours.append([[], []])

            string = (
                '    <path\n'
                '        stroke="black"\n'
                '        stroke-width="2"\n'
                '        fill="evenodd"\n'
                '        d="\n'
            )
            for flags, coordinates in contours[:-1]:
                string += calc_path(flags, coordinates, matrix)
            else:
                string += ' ' * 8 + '"\n'
                string += ' ' * 4 + '/>'

        return string

class TTFGlyfGlyph(object):
    def __init__(self, fin):
        (
            self.number_of_contours,
            self.x_min,
            self.y_min,
            self.x_max,
            self.y_max,
        ) = struct.unpack('>5h', fin.read(0xa))

        if self.number_of_contours < 0:
            self.glyph_type = 'composite'
        else:
            self.glyph_type = 'simple'


        if self.glyph_type == 'simple':
            self.end_pts_of_contours = struct.unpack(
                '>{0}H'.format(self.number_of_contours),
                fin.read(2 * self.number_of_contours)
            )
            self.instruction_length, = struct.unpack('>H', fin.read(2))
            self.instructions = fin.read(self.instruction_length)  # TODO

            self.flags = []
            while len(self.flags) < self.end_pts_of_contours[-1] + 1:
                flag, = struct.unpack('>B', fin.read(1))
                self.flags.append(flag)
                if flag & 0x08:  # repeat
                    repeat_count, = struct.unpack('>B', fin.read(1))
                    self.flags.extend([flag] * repeat_count)

            self.x_coordinates = []
            for flag in self.flags:
                if flag & 0x02:  # x-short vector
                    x, = struct.unpack('>B', fin.read(1))
                    if not flag & 0x10:  # (not) positive x-short vector
                        x *= -1
                else:
                    if flag & 0x10:  # this x is same
                        x = 0
                    else:
                        x, = struct.unpack('>h', fin.read(2))

                self.x_coordinates.append(x)

            self.y_coordinates = []
            for flag in self.flags:
                if flag & 0x04:  # y-short vector
                    y, = struct.unpack('>B', fin.read(1))
                    if not flag & 0x20:  # (not) positive y-short vector
                        y *= -1
                else:
                    if flag & 0x20:  # this y is same
                        y = 0
                    else:
                        y, = struct.unpack('>h', fin.read(2))

                self.y_coordinates.append(y)

            self.coordinates = zip(
                self.x_coordinates, self.y_coordinates
            )

            self.remainder = fin.read()
            if self.remainder.strip('\x00'):
                print 'XXX', `self.remainder`

        elif self.glyph_type == 'composite':
            self.components = []
            more_components = True
            while more_components:
                component = TTFGlyfComponent(fin)
                self.components.append(component)
                more_components = component.flag & 0x0020

class TTFGlyfComponent(object):
    def __init__(self, fin):
        (
            self.flag,
            self.glyph_index,
        ) = struct.unpack('>2H', fin.read(4))
        if self.flag & 0x0001:  # arg1 and 2 are words
            if self.flag & 0x0002:  # args are xy values; XXX
                fmt = '>2h'
            else:
                fmt = '>2H'
        else:
            if self.flag & 0x0002:
                fmt = '>2b'
            else:
                fmt = '>2B'
        (
            self.arg1, self.arg2
        ) = struct.unpack(fmt, fin.read(struct.calcsize(fmt)))

        if self.flag & 0x0008:  # we have a scale
            a = f2dot14(fin.read(2))
            b, c, d = 0.0, 0.0, a
        elif self.flag & 0x0040:  # we have an x and y scale
            a = f2dot14(fin.read(2))
            b, c = 0.0, 0.0
            d = f2dot14(fin.read(2))
        elif self.flag & 0x0080:  # we have a two by two
            a, b, c, d = [f2dot14(fin.read(2)) for i in range(4)]
        else:
            (a, b), (c, d) = [[1.0, 0.0], [0.0, 1.0]]

        self.matrix = [[a, b], [c, d]]


def fixed(uint32_t):
    return struct.unpack('>i', uint32_t)[0] / 65536.0

def f2dot14(uint16_t):
    return struct.unpack('>h', uint16_t)[0] / 16384.0

def long_date_time(uint64_t):
    seconds, = struct.unpack('>q', uint64_t)
    time = (datetime.datetime(1904, 1, 1) + datetime.timedelta(0, seconds))
    return time.timetuple()[:6]

def pascal_string(fin):
    length = ord(fin.read(1))
    return fin.read(length)

def calc_path(flags, coordinates, matrix):
    l = len(flags)
    string = ' ' * 0xc
    (a, b), (c, d) = matrix

    for i, f in enumerate(flags):
        x1, y1 = coordinates[(i+1)%l]
        x2, y2 = coordinates[(i+2)%l]

        f1 = flags[(i+1)%l]
        f2 = flags[(i+2)%l]

        # ------------------------------------------------------------------- #
        #  i    i+1  i+2
        #  on   on        ->  L x1 y1
        #  on   off  on   ->  Q x1 y1 x2 y2
        #  on   off  off  ->  Q x1 y1 ave(x1, x2) ave(y1, y2)
        #  off  on        ->  (pass)
        #  off  off  on   ->  T x2 y2  (or)  Q x1 y1 x2 y2
        #  off  off  off  ->  Q x1 y1 ave(x1, x2) ave(y1, y2)
        #
        #  where ave(s, t) = (s + t) / 2.0
        # ------------------------------------------------------------------- #

        if i == 0:
            if f & 0x01:  # on curve
                x, y = coordinates[i]
                string += 'M {} {}\n'.format(x, y)
                string += ' ' * 0xc
                if f1 & 0x01:
                    string += 'L {} {}\n'.format(x1, y1)
                elif f2 & 0x01:
                    string += 'Q {} {} {} {}\n'.format(x1, y1, x2, y2)
                else:
                    string += 'Q {} {} {} {}\n'.format(
                        x1, y1, (x1+x2)/2.0, (y1+y2)/2.0
                    )
            else:
                if f1 & 0x01:
                    string += 'M {} {}\n'.format(x1, y1)
                elif f2 & 0x01:
                    x, y = coordinates[i]
                    string += 'M {} {}\n'.format((x+x1)/2.0, (y+y1)/2.0)
                    string += ' ' * 0xc
                    string += 'Q {} {} {} {}\n'.format(x1, y1, x2, y2)
                else:
                    x, y = coordinates[i]
                    string += 'M {} {}\n'.format((x+x1)/2.0, (y+y1)/2.0)
                    string += ' ' * 0xc
                    string += 'Q {} {} {} {}\n'.format(
                        x1, y1, (x1+x2)/2.0, (y1+y2)/2.0
                    )
            continue

        if f & 0x01:
            string += ' ' * 0xc
            if f1 & 0x01:
                string += 'L {} {}\n'.format(x1, y1)
            elif f2 & 0x01:
                string += 'Q {} {} {} {}\n'.format(x1, y1, x2, y2)
            else:
                string += 'Q {} {} {} {}\n'.format(x1, y1, (x1+x2)/2.0, (y1+y2)/2.0)
        elif f1 & 0x01:
            continue
        elif f2 & 0x01:
            string += ' ' * 0xc
            string += 'T {} {}\n'.format(x2, y2)
        else:
            string += ' ' * 0xc
            string += 'Q {} {} {} {}\n'.format(x1, y1, (x1+x2)/2.0, (y1+y2)/2.0)
    else:
        string += ' ' * 0xc + 'z\n'

    return string


def dump(fin):
    ttf_obj = TTFObject(fin)
    ttf_obj.head = TTFHead(ttf_obj)
    ttf_obj.hhea = TTFHHea(ttf_obj)
    ttf_obj.maxp = TTFMaxP(ttf_obj)
    ttf_obj.name = TTFName(ttf_obj)
    ttf_obj.os_2 = TTFOS_2(ttf_obj)
    ttf_obj.post = TTFPost(ttf_obj)
    ttf_obj.cmap = TTFCMap(ttf_obj)
    ttf_obj.hmtx = TTFHMtx(ttf_obj)
    ttf_obj.loca = TTFLoca(ttf_obj)
    ttf_obj.glyf = TTFGlyf(ttf_obj)

    return ttf_obj
