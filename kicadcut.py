#!/usr/bin/env python
import os
import sys
import fnmatch
from pathlib import Path

import graphtec
import optimize
import math
from kicad_parser import KicadPCB

output_file = sys.stdout
offset = (10, 10)
border = (10, 10)
matrix = (1, 0, 0, 1)
speed = [2, 2]
force = [8, 30]
cut_mode = 0
input_filename = ''
input_layer = ''
media_size = (12*25.4, 12*25.4)
theta = 0
shrinkabs = 0.05
shrinkrel = 0.0
comp = 0.02
pdf = False
filters = []
orientation = 0

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def rotate(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    """
    ox, oy = origin
    px, py = point

    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy


def get_reference(footprint):
    for t in footprint.fp_text:
        if t[0] == 'reference':
            return t[1].strip('\"')
    return None

def parse_file(file, layer, _filters, _shrinkabs, _shrinkrel):
    pcb = KicadPCB.load(file)

    footprints = pcb.footprint if len(pcb.footprint) else pcb.module

    _strokes = []

    for footprint in footprints:
        at = footprint.at
        footprint_center_x = at[0]
        footprint_center_y = at[1]
        footprint_angle = (math.radians(at[2]) if len(at) > 2 else 0) 

        reference = get_reference(footprint)

        if (len(_filters) and (reference is None or not any(fnmatch.fnmatch(reference, filter) for filter in _filters))):
            continue

        for p in footprint.pad:
            pad_type = p[1]
            # shape = p[2]
            layers = [x.strip('\"') for x in p.layers]
            if pad_type == 'smd' and layer in layers:
                at = p.at
                size = p.size
                center_x = footprint_center_x + at[0]
                center_y = footprint_center_y + at[1]
                pad_angle = (math.radians(at[2]) if len(at) > 2 else 0)  - math.radians(180)
                
                width = size[0] - _shrinkabs - size[0] * _shrinkrel
                height = size[1] - _shrinkabs - size[1] * _shrinkrel

                if width > 0 and height > 0:
                    top_left = (center_x - width / 2, center_y - height / 2)
                    top_right = (center_x + width / 2, center_y - height / 2)
                    bottom_left = (center_x - width / 2, center_y + height / 2)
                    bottom_right = (center_x + width / 2, center_y + height / 2)

                    top_left = rotate((center_x, center_y), top_left, footprint_angle - pad_angle)
                    top_right = rotate((center_x, center_y), top_right, footprint_angle - pad_angle)
                    bottom_left = rotate((center_x, center_y), bottom_left, footprint_angle - pad_angle)
                    bottom_right = rotate((center_x, center_y), bottom_right,footprint_angle - pad_angle)
                        
                    top_left = rotate((footprint_center_x, footprint_center_y), top_left, -footprint_angle)
                    top_right = rotate((footprint_center_x, footprint_center_y), top_right, -footprint_angle)
                    bottom_left = rotate((footprint_center_x, footprint_center_y), bottom_left, -footprint_angle)
                    bottom_right = rotate((footprint_center_x, footprint_center_y), bottom_right, -footprint_angle)

                    stroke = [
                        [top_left[0], top_left[1]],
                        [top_right[0], top_right[1]],
                        [bottom_right[0], bottom_right[1]],
                        [bottom_left[0], bottom_left[1]]
                    ]

                    _strokes.append(stroke)

    return _strokes

def ints(str_ints):
    return list(map(int, str.split(str_ints, ',')))


def floats(str_floats):
    return list(map(float, str.split(str_floats, ',')))


def strings(str_strings):
    return str.split(str_strings, ',')
    
argc = 1
while argc < len(sys.argv):
    arg = sys.argv[argc]
    if arg == '--file':
        output_file = open(sys.argv[argc + 1], "w")
        argc = argc + 2
    elif arg == '--offset':
        offset = floats(sys.argv[argc + 1])
        argc = argc + 2
    elif arg == '--border':
        border = floats(sys.argv[argc + 1])
        argc = argc + 2
    elif arg == '--matrix':
        matrix = floats(sys.argv[argc + 1])
        argc = argc + 4
    elif arg == '--speed':
        speed = ints(sys.argv[argc + 1])
        argc = argc + 2
    elif arg == '--force':
        force = ints(sys.argv[argc + 1])
        argc = argc + 2
    elif arg == '--cut_mode':
        cut_mode = int(sys.argv[argc + 1])
        argc = argc + 2
    elif arg == '--media':
        media_size = floats(sys.argv[argc + 1])
        media_size = (min(media_size), max(media_size))
        argc = argc + 2
    elif arg == '--rotate':
        theta = float(sys.argv[argc + 1])
        argc = argc + 2
    elif arg == '--shrink_abs':
        shrinkabs = float(sys.argv[argc + 1])
        argc = argc + 2
    elif arg == '--shrink_rel':
        shrinkrel = float(sys.argv[argc + 1]) / 100
        argc = argc + 2
    elif arg == '--pdf':
        pdf = True
        argc = argc + 1
    elif arg == '--filter':
        filters = strings(sys.argv[argc+1])
        argc = argc + 2
    elif arg == '--comp':
        comp = float(sys.argv[argc+1])
        argc = argc + 2
    elif arg == '--orientation':
        orientation = int(sys.argv[argc+1])
        argc = argc + 2        
    else:
        if input_filename:
            input_layer = sys.argv[argc]
        else:
            input_filename = sys.argv[argc]
        argc = argc + 1

if not input_filename and not input_layer:
    eprint('usage: kicadcut [options] <filename> <layer>')
    eprint()
    eprint(' --offset {{x}},{{y}}\t\t\tOffset stencil by x and y in mm. Default: {}.'.format(offset))
    eprint(' --border {{h}},{{v}}\t\t\tCut a border around stencil using the specified horizontal and vertical margin. Default: {}.'.format(border))
    eprint(' --matrix {{a}},{{b}},{{c}},{{d}}\t\tLinear map (to correct spatial miscalibration). Default: {}.'.format(matrix))
    eprint(' --speed {{s}}[,{{s}}]\t\t\tSpeed for each pass. Default: {}.'.format(speed))
    eprint(' --force {{f}}[,{{f}}]\t\t\tForce for each pass. Default: {}.'.format(force))
    eprint(' --cut_mode {{mode}}\t\t\t0 = Precise, 1 = Fast. Default: {}.'.format(cut_mode))
    eprint(' --media {{w}},{{h}}\t\t\tMedia width and height in mm. Default: {}.'.format(media_size))
    eprint(' --rotate {{angle}}\t\t\tRotate cut by the specified angle in degrees. Default: {}.'.format(theta))
    eprint(' --shrink_abs {{l}}\t\t\tShrink pad width/height by absolute amount specified in mm. Default: {}.'.format(shrinkabs))
    eprint(' --shrink_rel {{l}}\t\t\tShrink pad width/height by relative amount specified in %. Default: {}.'.format(shrinkrel))
    eprint(' --filter {f}[,{f}]\t\t\tFilter components to include in stencil by reference. Wildcards (* and ?) can be used')
    eprint(' --comp {{l}}\t\t\t\tOvercut compensation length adjustment in mm. Default: {}.'.format(comp))
    eprint(' --orientation {{o}}\t\t\tSet orientation (0 = portrait, 1 = landscape). Default: {}.'.format(orientation))
    eprint(' --pdf\t\t\t\t\tGenerate PDF of the stencil')
    sys.exit(1)

strokes = parse_file(input_filename, input_layer, filters, shrinkabs, shrinkrel)

if len(strokes) == 0:
    eprint('Error: no pads found')
    sys.exit(1)


g = graphtec.graphtec(output_file, orientation, comp)

g.set(media_size=media_size)
g.set(offset=(offset[0] + border[0] + 10, offset[1] + border[1]))
g.set(matrix=matrix)

g.start()

strokes = optimize.rotate(strokes, theta)
strokes = optimize.justify(strokes)
max_x, max_y = optimize.max_extent(strokes)

border_path = [
    (-border[0], -border[1]),
    (max_x + border[0], -border[1]),
    (max_x + border[0], max_y + border[1]),
    (-border[0], max_y + border[1])
]

if cut_mode == 0:
    lines = optimize.optimize(strokes, border)
    for (_speed, f) in zip(speed, force):
        g.set(speed=_speed, force=f, acceleration=3)
        for arg in lines:
            g.line(*arg)
        if border[0] != 0 or border[1] != 0:
            g.closed_path(border_path)
else:
    for (_speed, f) in zip(speed, force):
        g.set(speed=_speed, force=f, acceleration=3)
        for _stroke in strokes:
            g.closed_path(_stroke)
        if border[0] != 0 or border[1] != 0:
            g.closed_path(border_path)

g.end()

print()

sys.stdout.flush()

eprint('File parsed: {} pads will be cut. Stencil width {:.1f}mm, height: {:.1f}mm'.format(len(strokes), max_x+2*border[0], max_y+2*border[1]))


if pdf:
    from fpdf import FPDF, FPDF_VERSION

    pdf = FPDF('P' if orientation==0 else 'L', 'mm', (media_size[0], media_size[1]) if orientation==0 else (media_size[0], media_size[1]) )
    pdf.add_page()
    pdf.set_line_width(0.0)
    pdf.set_margins(0.0, 0.0)
    pdf.set_creator("KiCadCut")
    pdf.set_author("https://github.com/ktand/Kicadcut")
    pdf.set_title(input_filename)
    pdf.set_subject(input_layer)
    # pdf.set_producer("FPDF {}".format(FPDF_VERSION))

    lines = optimize.optimize(strokes, border)

    offset_lines = [
        [x1 + offset[0] + border[0] + 10, y1 + offset[1] + border[1], x2 + offset[0] + border[0]  + 10, y2 + offset[1] + border[1]] for x1, y1, x2, y2 in lines]

    for arg in offset_lines:
        dx1,dy1,dx2,dy2 = g.comp(arg[0], arg[1], arg[2], arg[3])
        pdf.line(arg[0]+dx1, arg[1]+dy1, arg[2]+dx2, arg[3]+dy2)
        # pdf.line(arg[0], arg[1], arg[2], arg[3])

    if border[0] != 0 or border[1] != 0:
        offset_border = [[x + offset[0] + border[0] + 10, y + offset[1] + border[1]] for x, y in border_path]

        pdf.line(offset_border[0][0], offset_border[0][1], offset_border[1][0], offset_border[1][1])
        pdf.line(offset_border[1][0], offset_border[1][1], offset_border[2][0], offset_border[2][1])
        pdf.line(offset_border[2][0], offset_border[2][1], offset_border[3][0], offset_border[3][1])
        pdf.line(offset_border[3][0], offset_border[3][1], offset_border[0][0], offset_border[0][1])

    output_filename = os.path.join(os.getcwd(), Path(input_filename).stem+'.pdf')

    pdf.output(output_filename)
