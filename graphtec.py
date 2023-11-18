#
# communicate with a graphtec printer (Silhouette Cameo or Portrait)
#

import sys
import math

class graphtec:
  def __init__(self, file, orientation, comp_dist):
    self.fd = file
    self.scale = 20 # mm to Silhouette unit 
    self.offset = (100,10)
    self.matrix = (1,0,0,1)
    self.media_size = (12*25.4, 12*25.4)   # default of 12x12 inches
    self.comp_dist = comp_dist
    self.orientation = orientation

  def emit(self, s):
    self.fd.write(s)

  def start(self):
    papertype = "100"
    trackenhancing = "0"
    page = ["media_size", int(self.scale*self.media_size[0]), int(self.scale*self.media_size[1])]
    self.emit("\x1b\x04")  # initialize plotter
    self.emit("\x1b\x05")  # status request
    self.emit("TG1\x03")   # mat 1
    self.emit("FN"+str(self.orientation)+"\x03") # set orientation
    self.emit("TB50,"+str(self.orientation)+"\x03") # set orientation
    self.emit("\\0,0\x03")
    self.emit("Z"+str(page[1])+","+str(page[2])+"\x03")
    self.emit("J1\x03")
    self.emit("TJ3\x03")
    self.emit("FC18,1,1\x03") # cutter offset
    self.emit("TJ3\x03")
    self.emit("FE0,1\x03")

  def end(self):
    self.emit("L0\x03")
    self.emit("\\0,0\x03")
    self.emit("M0,0\x03")    
    self.emit("J0\x03")      
    self.emit("FN0\x03")     
    self.emit("TB50,0\x03")  
    self.emit("\x1b\x05")

  def transform(self, x, y):
    tx = self.matrix[0]*x + self.matrix[1]*y + self.offset[0]
    ty = self.matrix[2]*x + self.matrix[3]*y + self.offset[1]
    tx = tx*self.scale
    ty = ty*self.scale
    return tx,ty

  def move(self, x, y):
    x,y = self.transform(x,y)
    self.emit('M%.3f,%.3f\x03' % ((x,y) if self.orientation == 1 else (y,x)))

  def draw(self, x, y):
    x,y = self.transform(x,y)
    self.emit('D%.3f,%.3f\x03' % ((x,y) if self.orientation == 1 else (y,x)))

  def closed_path(self, s):
    if len(s)<3:
      return
    self.move(*s[0])
    for p in s[1:]:
      self.draw(*p)
    self.draw(*s[0])

  def path(self, s):
    self.move(*s[0])
    for p in s[1:]:
      self.draw(*p)

  def comp(self, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    theta = math.atan2(dy,dx)
    dist_pre = -self.comp_dist
    dist_post = self.comp_dist
    dx1 = dist_pre*math.cos(theta)
    dy1 = dist_pre*math.sin(theta)
    dx2 = dist_post*math.cos(theta)
    dy2 = dist_post*math.sin(theta)
    return (dx1,dy1,dx2,dy2)

  def line(self, x1, y1, x2, y2):
    dx1,dy1,dx2,dy2 = self.comp(x1,y1,x2,y2)
    self.move(x1+dx1,y1+dy1)
    self.draw(x2+dx2,y2+dy2)

  def set(self, **kwargs):
    for k in kwargs:
      if k=='acceleration':
        self.emit("TJ" + str(kwargs[k]) + "\x03")
      if k=='speed':
        self.emit("!" + str(kwargs[k]) + ",1\x03")
      elif k=='force':
        self.emit("FX" + str(kwargs[k]) + ",1\x03")
      elif k=='offset':
        self.offset = kwargs[k]
      elif k=='matrix':
        self.matrix = kwargs[k]
      elif k=='media_size':
        self.media_size = kwargs[k]
