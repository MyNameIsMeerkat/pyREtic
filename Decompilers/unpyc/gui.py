#!/usr/bin/python

# [The "BSD licence"]
# Copyright (c) 2008-2009 Dmitri Kornev
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * The name of the author may not be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Dmitri Kornev BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''
Tk vizualization of L{CodeBlocks}.

No intentions to support/modify this module.
Plugin for IDA Pro is more probable.

'''

from Tkinter import *
import random

AppInstance = None

def scrollUp(event):
    AppInstance.canvas.yview_scroll(1, 'units')

def scrollDown(event):
    AppInstance.canvas.yview_scroll(-1, 'units')

def callback():
    print 'called the callback!'

def MenuExitBtn():
    exit()

def mouseDown(event):
    AppInstance.bx = event.x
    AppInstance.by = event.y
    event.widget.bind('<Motion>', Motion)

def Motion(event):
    dx = event.x - AppInstance.bx
    dy = event.y - AppInstance.by
    AppInstance.textBoxes[event.widget].moveBy(dx, dy)

def mouseUp(event):
    event.widget.unbind('<Motion>')

class EmptyApp:
    def __init__(self):
        global AppInstance
        if AppInstance is not None:
            print 'Error! Only one instance of App is possible!'
            return None

        root = Tk();
        root.title('Gui Test')
        root.geometry('%dx%d' % (root.winfo_screenwidth(),
                                 root.winfo_screenheight()))

        # 0,0 is top left corner
        # increases down, right
        canvas = Canvas(bg='white', scrollregion=(0,0,2000,100000))
        canvas.place(x=0, y=0, height=10000, width=2000)

        scrollY = Scrollbar(root, orient=VERTICAL, command=canvas.yview)
        scrollY.place(anchor=NE, relx=1, rely=0, relheight=1)
        canvas.config(yscrollcommand=scrollY.set)
        scrollX = Scrollbar(root, orient=HORIZONTAL, command=canvas.xview)
        scrollX.place(anchor=SW, relx=0, rely=1, relwidth=1)
        canvas.config(xscrollcommand=scrollX.set)
        canvas.bind('<Button-4>', scrollDown)
        canvas.bind('<Button-5>', scrollUp)

        menu = Menu(root)
        root.config(menu=menu, bg='white')

        filemenu = Menu(menu)
        menu.add_cascade(label='File', underline=0, menu=filemenu)
        filemenu.add_command(label='New', underline=0, command=callback)
        filemenu.add_command(label='Open...', underline=0, command=callback)
        filemenu.add_separator()
        filemenu.add_command(label='Exit', underline=1, command=MenuExitBtn)

        helpmenu = Menu(menu)
        menu.add_cascade(label='Help', underline=0, menu=helpmenu)
        helpmenu.add_command(label='About...', underline=0, command=callback)

        self.textBoxes = {}
        self.root = root
        self.canvas = canvas
        self.menu = menu
        self.BlocksStep = 20
        self.bx = 0
        self.by = 0

        # little global pollution
        AppInstance = self

    def connectBlocks(self, b1, b2, xref):
        f1 = b1.frame
        f2 = b2.frame
        f1.update_idletasks()
        f2.update_idletasks()

        color = 'blue'
        if xref in ('JIF', 'JIT'): color = 'green'
        elif xref in ('NJIF', 'NJIT'): color = 'red'
        elif xref in ('try', 'except', 'finally'): color = 'black'

        x1 = f1.winfo_x() + f1.winfo_width()/2
        y1 = f1.winfo_y() + f1.winfo_height()
        x2 = f2.winfo_x() + f2.winfo_width()/2
        y2 = f2.winfo_y()
        l = self.canvas.create_line(x1, y1, x1, y1 + self.BlocksStep,
                                    x2, y2 - self.BlocksStep, x2, y2,
                                    width=2, arrow=LAST, fill=color, smooth=1)
        b1.addOFrame(b2)
        b1.addOLine(l)
        b2.addIFrame(b1)
        b2.addILine(l)
        return l

    def start(self):
        self.root.mainloop();

    class TextBox:
        def __init__(self, text, x=0, y=0):
            frameBorder = 2
            textBorder = 1
            textPadx = 4
            textPady = 4
            titleHeight = 10
            frame = Frame(AppInstance.canvas, bg='lightblue', relief='groove',
                          bd=frameBorder)
            widget = Text(frame, fg='black', bg='lightgreen', relief='groove',
                          bd=textBorder, padx=textPadx, pady=textPady)
            widget.insert(END, text)
            lines = text.split('\n')
            maxl = 0
            for line in lines:
                if len(line) > maxl:
                    maxl = len(line)
            if maxl < 50:
                maxl = 50
            widget.config(state=DISABLED, height=len(lines), width=maxl)
            #widget.config(height=len(lines), width=maxl)
            widget.place(x=0, y=titleHeight)
            widget.update_idletasks()
            lw = widget.winfo_width()
            lh = widget.winfo_height()
            frame.place(x=x, y=y, width=lw+2*frameBorder,
                        height=lh+titleHeight+2*frameBorder)
            window = AppInstance.canvas.create_window(x, y, anchor=NW,
                                          window=frame,
                                          width=lw+2*frameBorder,
                                          height=lh+titleHeight+2*frameBorder)
            frame.bind('<ButtonPress-1>', mouseDown)
            frame.bind('<ButtonRelease-1>', mouseUp)

            AppInstance.textBoxes[frame] = self
            self.frame = frame
            self.text = widget
            self.window = window
            self.iFrames = []
            self.iLines = []
            self.oFrames = []
            self.oLines = []

        def addIFrame(self, frame):
            self.iFrames.append(frame)

        def addOFrame(self, frame):
            self.oFrames.append(frame)

        def addILine(self, line):
            self.iLines.append(line)

        def addOLine(self, line):
            self.oLines.append(line)

        def moveBy(self, dx, dy):
            c = AppInstance.canvas.coords(self.window)
            self.moveTo(c[0]+dx, c[1]+dy)

        def moveTo(self, x, y):
            step = 20
            AppInstance.canvas.coords(self.window, x, y)
            for line in self.iLines:
                c = AppInstance.canvas.coords(line)
                AppInstance.canvas.coords(line, c[0], c[1], c[2], c[3],
                                          x + self.frame.winfo_width() / 2,
                                          y - step,
                                          x + self.frame.winfo_width() / 2,
                                          y)
            for line in self.oLines:
                c = AppInstance.canvas.coords(line)
                AppInstance.canvas.coords(line,
                                         x + self.frame.winfo_width() / 2,
                                         y + self.frame.winfo_height(),
                                         x + self.frame.winfo_width() / 2,
                                         y + step + self.frame.winfo_height(),
                                         c[4], c[5], c[6], c[7])

        def height(self):
            self.frame.update_idletasks()
            return self.frame.winfo_height()

        def width(self):
            self.frame.update_idletasks()
            return self.frame.winfo_width()



class App:
    def __init__(self, disassembler):
        self.disassembler = disassembler

    def start(self):
        def cmp(x,y):
            if x < y: return -1
            if x > y: return 1
            return 0

        def whichBlock(i, a):
            b = -1
            for s in a:
                if i < s:
                    return b
                b += 1
            return b

        ga = EmptyApp()
        cb = self.disassembler.getAllCodeBlocks()
        a = sorted(cb.blocks.keys())

        l = len(self.disassembler.co.code.value)
        y = 0

        tbs = []
        nl = {}
        for i in range(len(a)):
            if i < len(a) - 1:
                code = self.disassembler.codeDisasm(a[i], a[i+1] - a[i])
                b = ga.TextBox(code, 300, y)
                y += b.height() + 10
                tbs.append(b)
            else:
                code = self.disassembler.codeDisasm(a[i], l - a[i])
                tbs.append(ga.TextBox(code, 300, y))
        for block in a:
            for s in cb.blocks[block]:
                ga.connectBlocks(tbs[whichBlock(s.blockxref, a)],
                                 tbs[whichBlock(block, a)], s.name)
                nl[whichBlock(s.blockxref, a)] = 1
        for block in a:
            if whichBlock(block, a) not in nl and \
               whichBlock(block, a) + 1 < len(tbs):
                ga.connectBlocks(tbs[whichBlock(block, a)],
                                 tbs[whichBlock(block, a) + 1], 2)
        ga.start()
