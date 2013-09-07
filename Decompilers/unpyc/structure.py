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

from copy import copy
import re
import traceback

from ast import *

# mergeCompoundNodes
from text import s_indentExText as indentExText, \
                 s_indentForText as indentForText, \
                 s_indentText as indentText

def dbgprint(s):
    '''
    print stub
    '''
    #print >> stderr, s
    pass

class edge:
    '''Class that defines edge in CFG.'''

    def __init__(self, fromNode, toNode, type=''):
        '''
        Constructor for new edge 'fromNode -> toNode'.

        @param fromNode: node at which edge starts.
        @param toNode: node at which edge ends.
        @param type: type of edge (t, f, for, AF, ...).

        '''
        self.fromNode = fromNode
        self.toNode = toNode
        self.type = type

    def __str__(self):
        return '%s -(%s)-> %s' % \
               (str(self.fromNode), str(self.type), str(self.toNode))

class node:
    '''Class that defines node in CFG.'''

    # TODO: incoming and outgoing should be hashes
    # CAUTION: all calls should be done via named parameters!
    def __init__(self, name, incoming, outgoing,
                 conditional=True, loop=False, forloop=False,
                 exceptNode=False, finallyNode=False,
                 code='', condition=None, offset=-1, length=-1):
        '''
        @param name: name of the node.
        @param incoming: incoming edges.
        @param outgoing: outgoing edges.
        @param conditional: whether the node is conditional or not.
        @param loop: whether the node is a head of a loop or not.
        @param forloop: whether the node is a head of a forloop or not.
        @param exceptNode:
            whether the node is a head of except block (SETUP_EXCEPT) or not.
        @param finallyNode:
            whether the node is a head of finally block (SETUP_FINALLY) or not.
        @param code: code associated with the node.
        @param condition:
            code associated with the condition of the conditional node.
        @param offset: offset of the node first command.
        @param length:
            length of the bytecode that is represented by this node. May
            become unreliable.

        '''
        self.name = name
        self.incoming = incoming
        self.outgoing = outgoing
        self.conditional = conditional
        self.loop = loop
        self.forloop = forloop
        self.exceptNode = exceptNode
        self.wasExceptNode = False
        self.finallyNode = finallyNode
        self.offset = offset
        self.length = length
        self.code = code
        self.condition = condition

    def __str__(self):
        r = str(self.name)
        r += '(%s)' % str(self.condition)
        r += '[%s]' % self.code
        r += ':\n\ti: ' + \
             ', '.join('%s(%s)' % (str(e.fromNode), e.type) \
                       for e in self.incoming) + \
             '\n\to: ' + \
             ', '.join('%s(%s)' % (str(e.toNode), e.type) \
                       for e in self.outgoing) + '\n'
        return r

class graph:
    '''Class that defines CFG and operations on it.'''

    def __init__(self, root, nodes, debugDraw=False):
        '''
        @param root: root node of the CFG.
        @param nodes: nodes of the CFG (L{node}).
        @param debugDraw:
            whether to save images of intermediate CFGs during
            processing or not.

        '''
        self.root = root
        self.nodes = nodes
        self.debugDraw = debugDraw
        self.debugDrawComment = ''
        # counter for debugDraw
        self.incnum = 0

    def __str__(self):
        r = 'r:%s\n' % self.root
        nk = sorted(self.nodes.keys())
        for n in nk:
            r += str(self.nodes[n])
        return r

    def intervals(self):
        '''
        Returns list of intervals.

        Given a node h, an interval I(h) is the maximal, single-entry
        subgraph in which h is the only entry node and in which all
        closed paths contain h. The unique interval node h is called
        the interval head or simply the header node.
        (from "Reverse Compilation Techniques" by Cristina Cifuentes).

        Currently this method is unused in unpyc project.

        @return: list of intervals of current CFG.

        '''
        I = []
        toH = []
        H = [self.root]
        for n in H:
            dbgprint('>>> ' + n)
            tI = set([n])
            newFlag = True
            while newFlag:
                newFlag = False
                toH = []
                for x in copy(tI):
                    dbgprint('>>> for ' + x)
                    for y in self.nodes[x].outgoing:
                        if y.toNode in tI: continue
                        okFlag = True
                        for z in self.nodes[y.toNode].incoming:
                            if z.fromNode not in tI: okFlag = False
                        if okFlag:
                            dbgprint('>>> adding ' + y.toNode)
                            tI.add(y.toNode)
                            newFlag = True
                        else:
                            if y.toNode not in H: toH.append(y.toNode)
            H.extend(toH)
            I.append(tI)
        return I

    def o_intervals(self):
        '''Old verstion of L{intervals}.'''

        I = []
        toH = []
        H = [self.root]
        for n in H:
            dbgprint('>>> ' + n)
            tI = set([n])
            newFlag = True
            while newFlag:
                newFlag = False
                toH = []
                for x in copy(tI):
                    dbgprint('>>> for ' + x)
                    for y in self.nodes[x].o:
                        if y in tI: continue
                        okFlag = True
                        for z in self.nodes[y].i:
                            if z not in tI: okFlag = False
                        if okFlag:
                            dbgprint('>>> adding ' + y)
                            tI.add(y)
                            newFlag = True
                        else:
                            if y not in H: toH.append(y)
            H.extend(toH)
            I.append(tI)
        return I

    def postorder(self):
        '''
        @return: list of nodes of current CFG in postorder.

        '''
        res = []
        stack = [self.root]
        visited = set()
        while len(stack):
            n = self.nodes[stack[-1]]
            if n.name in visited:
                res.append(n.name)
                stack.pop()
            visited.add(n.name)
            for c in n.outgoing:
                if c.toNode not in visited:
                    stack.append(c.toNode)
        return res

    def updateEdges(self, oldname, newname):
        '''
        Updates fromNode and toNode in all edges replacing oldname -> newname.

        @param oldname: previous name of the node.
        @param newname: new name of the node.

        '''
        toDelete = []
        for ie in self.nodes[oldname].incoming:
            if ie.fromNode == '0': continue
            for x in xrange(len(self.nodes[ie.fromNode].outgoing)):
                if self.nodes[ie.fromNode].outgoing[x].toNode == oldname:
                    a = [e.toNode for e in self.nodes[ie.fromNode].outgoing]
                    if newname not in a:
                        self.nodes[ie.fromNode].outgoing[x].toNode = newname
                    else:
                        toDelete.append((ie.fromNode, x))
        for (a, b) in toDelete:
            del self.nodes[a].outgoing[b]
        toDelete = []
        for oe in self.nodes[oldname].outgoing:
            for x in xrange(len(self.nodes[oe.toNode].incoming)):
                if self.nodes[oe.toNode].incoming[x].fromNode == oldname:
                    a = [e.fromNode for e in self.nodes[oe.toNode].incoming]
                    if newname not in a:
                        self.nodes[oe.toNode].incoming[x].fromNode = newname
                    else:
                        toDelete.append((oe.toNode, x))
        for (a, b) in toDelete:
            del self.nodes[a].incoming[b]

    def removeEdge(self, fromNode, toNode):
        for index in xrange(len(fromNode.outgoing)):
            if fromNode.outgoing[index].toNode == toNode.name:
                del fromNode.outgoing[index]
                break
        for index in xrange(len(toNode.incoming)):
            if toNode.incoming[index].fromNode == fromNode.name:
                del toNode.incoming[index]
                break

    def addEdge(self, fromNode, toNode, type=''):
        e = edge(fromNode.name, toNode.name, type)
        fromNode.outgoing.append(e)
        toNode.incoming.append(e)

    def doDebugDraw(self):
        '''Save CFG as png image in current working directory.'''

        if self.debugDraw:
            self.savePythonGraph('%d %s' % (self.incnum,
                                            self.debugDrawComment))
            self.incnum += 1

    def newDebugDrawIteration(self, comment=''):
        self.incnum += 100 - self.incnum % 100
        self.debugDrawComment = comment

    @staticmethod
    def findEdges(node, *edgeTypes):
        '''
        @param node: node whose outgoing edges to watch.
        @param edgeTypes: list of edge types to search, should be unique.
        @return:
            list of edges of the given type in the same order.
            If edge was not found None is returned in its place.

        '''
        h = {}
        for t in edgeTypes: h[t] = None
        for e in node.outgoing:
            if e.type in h:
                h[e.type] = e
        return [h[t] for t in edgeTypes]

    @staticmethod
    def findTrueFalseEdge(n):
        return graph.findEdges(n, 't', 'f')

    @staticmethod
    def findLoopALEdge(n):
        return graph.findEdges(n, 'loop', 'AL')

    @staticmethod
    def findForAFEdge(n):
        return graph.findEdges(n, 'for', 'AF')

    @staticmethod
    def findTryExceptEdge(n):
        return graph.findEdges(n, 'try', 'except')

    @staticmethod
    def findASFASF2finallyEdge(n):
        return graph.findEdges(n, 'ASF', 'ASF2', 'finally')

    def mergeComplexNodes(self, x, y, how):
        '''
        Merges two nodes.

        @param x: first (higher) node.
        @param y: second (lower) node.
        @param how: one of these:
            0. x or y
            1. x and y
            2. not x or y
            3. not x and y

        '''
        # TODO: validate!

        dbgprint('merging nodes %s and %s how=%d' % (x.name, y.name, how))

        if isinstance(x, node):
            nx = x
            x = x.name
        else:
            nx = self.nodes[x]
        if isinstance(y, node):
            ny = y
            y = y.name
        else:
            ny = self.nodes[y]

        i = nx.incoming
        o = ny.outgoing

        # TODO: could break here... choose minimum
        # TODO: offset of the new node?
        newname = str(nx.name) + '&' + str(ny.name)
        if how == 0:
            c = BooleanOROp(nx.condition, ny.condition)
            # TODO: check, that ny.code == '' else warning
            n = node(newname, i, o, conditional=True, condition=c,
                     code=nx.code, offset=nx.offset)
        elif how == 1:
            
            c = BooleanANDOp(nx.condition, ny.condition)
            n = node(newname, i, o, conditional=True, condition=c,
                     code=nx.code, offset=nx.offset)
        elif how == 2:
            c = BooleanOROp(BooleanNOTOp(nx.condition), ny.condition)
            n = node(newname, i, o, conditional=True, condition=c,
                     code=nx.code, offset=nx.offset)
        elif how == 3:
            c = BooleanANDOp(BooleanNOTOp(nx.condition), ny.condition)
            n = node(newname, i, o, conditional=True, condition=c,
                     code=nx.code, offset=nx.offset)
        self.nodes[n.name] = n
        self.updateEdges(x, newname)
        self.updateEdges(y, newname)
        if self.root in (x, y):
            self.root = newname
        del (self.nodes[x], self.nodes[y])
        

    def simplifyComplexIFs(self):
        '''
        Structures short ciruit evaluation of conditions.

        '''
        # for drawing
        self.newDebugDrawIteration('simplifyComplexIFs')
        self.doDebugDraw()

        changes = True
        while changes:
            changes = False
            pnodes = self.postorder()
            for nname in pnodes:
                n = self.nodes[nname]
                # TODO: 3 types of conditional blocks
                # (nonconditional, semiconditional, conditional-only)
                if n.conditional:

                    self.doDebugDraw()

                    (te, fe) = self.findTrueFalseEdge(n)
                    (tn, fn) = (self.nodes[te.toNode], self.nodes[fe.toNode])
                    if tn.conditional and len(tn.incoming) == 1:
                        (te2, fe2) = self.findTrueFalseEdge(tn)
                        tn2 = self.nodes[te2.toNode]
                        fn2 = self.nodes[fe2.toNode]
                        if fn2.name == fn.name:
                            self.mergeComplexNodes(n, tn, 1)
                            changes = True
                            continue
                        if tn2.name == fn.name:
                            self.mergeComplexNodes(n, tn, 2)
                            changes = True
                            continue
                    if fn.conditional and len(fn.incoming) == 1:
                        (te2, fe2) = self.findTrueFalseEdge(fn)
                        tn2 = self.nodes[te2.toNode]
                        fn2 = self.nodes[fe2.toNode]
                        if tn2.name == tn.name:
                            self.mergeComplexNodes(n, fn, 0)
                            changes = True
                            continue
                        if fn2.name == tn.name:
                            self.mergeComplexNodes(n, fn, 3)
                            changes = True
                            continue

            # drawing stuff
            if changes:
                self.doDebugDraw()

    def mergeCompoundNodes(self, head, x, y, latch):
        '''
        Merges two nodes in if/else construction.

        @param x: first (higher) node.
        @param y: second (lower) node.

        '''
        # TODO: add optimization for latch node to avoid simplifyConsecutive
        if y is None or y.code == '':
            if x.code == '': x.code = 'pass\n'
            if isinstance(head.condition, CompareOp) and \
               head.condition.value == 'EXC_MATCH':
                code = head.code + 'except ' + \
                       str(head.condition.children[1]) + indentExText(x.code)
            else:
                code = head.code + 'if ' + \
                       str(head.condition) + ':\n' + indentText(x.code, 1)
                       #+ '\n' + latch.code
            n = node(head.name, head.incoming, x.outgoing,
                     conditional=False, code=code, offset=head.offset)
        else:
            if x.code == '': x.code = 'pass\n'
            if y.code == '': y.code = 'pass\n'
            if isinstance(head.condition, CompareOp) and \
               head.condition.value == 'EXC_MATCH':
                if y.conditional:
                    code = head.code + 'except ' + \
                           str(head.condition.children[1]) + \
                           indentExText(x.code) + y.code
                else:
                    code = head.code + 'except ' + \
                           str(head.condition.children[1]) + \
                           indentExText(x.code) + \
                           'except:\n' + indentText(y.code, 1)
            else:
                code = head.code + 'if ' + str(head.condition) + ':\n' + \
                       indentText(x.code, 1) + \
                       'else:\n' + indentText(y.code, 1)# + '\n' + latch.code
            n = node(head.name, head.incoming, x.outgoing,
                     conditional=False, code=code, offset=head.offset)

        self.nodes[head.name] = n
        self.updateEdges(x.name, head.name)
        if y is not None: self.updateEdges(y.name, head.name)
        del self.nodes[x.name] #, self.nodes[latch.name])
        if y is not None: del self.nodes[y.name]

    def preprocessWhileLoops(self):
        '''
        Finds while loops and marks first conditional node as unconditional.

        '''
        self.newDebugDrawIteration('preprocessWhileLoops')
        self.doDebugDraw()

        for nname in self.nodes:
            n = self.nodes[nname]
            if n.loop:

                self.doDebugDraw()

                (loope, ALe) = self.findLoopALEdge(n)
                (loop, AL) = (self.nodes[loope.toNode], self.nodes[ALe.toNode])
                if not loop.forloop: loop.conditional = False

    def structureSingleConditional(self, n):
        '''
        @return: True, if conditional was structured, False otherwise.

        '''
        (te, fe) = self.findTrueFalseEdge(n)
        (tn, fn) = (self.nodes[te.toNode], self.nodes[fe.toNode])
        if len(tn.outgoing) == 1 and tn.outgoing[0].toNode == fn.name and \
           tn.outgoing[0].type != 'AE':
            self.mergeCompoundNodes(n, tn, None, fn)
            return True
        if len(fn.outgoing) == 1 and fn.outgoing[0].toNode == tn.name and \
           fn.outgoing[0].type != 'AE':
            n.condition = BooleanNOTOp(n.condition)
            self.mergeCompoundNodes(n, fn, None, tn)
            return True
        if len(fn.outgoing) == 1 and len(tn.outgoing) == 1 and \
           tn.outgoing[0].toNode == fn.outgoing[0].toNode and \
           tn.outgoing[0].type != 'AE' and \
           fn.outgoing[0].type != 'AE':
            if tn.offset < fn.offset:
                latch = self.nodes[tn.outgoing[0].toNode]
                self.mergeCompoundNodes(n, tn, fn, latch)
                return True
            else:
                n.condition = BooleanNOTOp(n.condition)
                latch = self.nodes[tn.outgoing[0].toNode]
                self.mergeCompoundNodes(n, fn, tn, latch)
                return True
        return False

    def structureSingleLoop(self, n):
        '''
        @return: True, if loop was structured, False otherwise.

        '''
        #THIS ONLY WORKS IF optimizeJumps = True
        self.extra.append(n)
        #print "N: ",n 
        (loope, ALe) = self.findLoopALEdge(n)
        #print "LOOPE: %s"%(loope)
        #print "ALe: %s"%(ALe)
        (loop, AL) = (self.nodes[loope.toNode], self.nodes[ALe.toNode])
        #print "LOOP: %s"%(loop)
        #print "AL: %s"%(AL)
        
        #Rich mod change test condition to look for t/f edges not loop property
        
        if loop.forloop:
            
            (forloope, AFe) = self.findForAFEdge(loop)
            forloop = self.nodes[forloope.toNode]
            AF = self.nodes[AFe.toNode]
            #if len(forloop.outgoing) == 1 and \
            #   forloop.outgoing[0].toNode == AF.name and \
            #   len(AF.outgoing) == 1 and AF.outgoing[0].toNode == AL.name:
            if 1:
                
                forloop.code = indentForText(forloop.code)
                if AF.code != '':
                    AF.code = 'else:\n' + indentText(AF.code, 1)
                    
                
                self.removeEdge(loop, AF)
                self.removeEdge(n, AL)
                return True
        else:
            try:
                (te, fe) = self.findTrueFalseEdge(loop)
                (tn, fn) = (self.nodes[te.toNode], self.nodes[fe.toNode])
                if len(tn.outgoing) == 1 and tn.outgoing[0].toNode == fn.name and \
                   len(fn.outgoing) == 1 and fn.outgoing[0].toNode == AL.name:
                    loop.code = 'while ' + str(loop.condition) + ':\n'
                    if tn.code == '': tn.code = 'pass\n'
                    tn.code = indentText(tn.code, 1)
                    if fn.code != '':
                        fn.code = 'else:\n' + indentText(fn.code, 1)
                    self.removeEdge(loop, fn)
                    self.removeEdge(n, AL)
                    return True
            except Exception, err:
                print "[X] Rich exception caught", err
                traceback.print_exc()
                return False

    def structureSingleExcept(self, n):
        '''
        @return: True, if except was structured, False otherwise.

        '''
        changes = False
        # T - try, E - except, F - finally
        # t - true, f - false
        # e - edge, n - node
        # c - child
        (Te, Ee) = self.findTryExceptEdge(n)
        (Tn, En) = (self.nodes[Te.toNode], self.nodes[Ee.toNode])
        tn = self.nodes[Ee.toNode]
        fn = self.nodes[Ee.toNode]
        (te, fe) = self.findTrueFalseEdge(fn)
        while fe is not None:
            (tn, fn) = (self.nodes[te.toNode], self.nodes[fe.toNode])
            (te, fe) = self.findTrueFalseEdge(fn)

        if tn.name != fn.name and len(tn.outgoing) == 1 and \
           len(fn.outgoing) == 1 and len(fn.incoming) == 1 and \
           fn.code == '':
            pn = self.nodes[fn.incoming[0].fromNode]
            self.removeEdge(pn, fn)
            self.addEdge(pn, self.nodes[tn.outgoing[0].toNode], 'f')
            changes = True

        if tn.name == fn.name:
            if not tn.code.startswith('except ') and \
               not tn.code.startswith('except:'):
                if tn.code == '': tn.code = 'pass\n'
                tn.code = 'except:\n' + indentText(tn.code, 1)
                changes = True

        # check if try block is structured
        TisOK = False
        if len(Tn.outgoing) == 1:
            Tnc = self.nodes[Tn.outgoing[0].toNode]
            for e in Tnc.incoming:
                if e.type == 'AE':
                    TisOK = True
                    break

        # find else block
        elsen = None
        if TisOK:
            if len(tn.outgoing) == 1 and \
               Tn.outgoing[0].toNode == tn.outgoing[0].toNode:
                elsen = None
            else:
                elsen = self.nodes[Tn.outgoing[0].toNode]

        # check if else block is structured
        elseisOK = False
        if TisOK:
            if elsen is None:
                elseisOK = True
            elif len(elsen.outgoing) == 1 and len(tn.outgoing) == 1 and \
                 elsen.outgoing[0].toNode == tn.outgoing[0].toNode:
                elseisOK = True

        # check if except block is structured
        EisOK = False
        if TisOK and elseisOK:
            # TODO: separate method
            for index in xrange(len(n.incoming)):
                if n.incoming[index].type == 'ASF':
                    n.incoming[index].type = 'ASF2'
                    pn = self.nodes[n.incoming[index].fromNode]
                    for index2 in xrange(len(pn.outgoing)):
                        if pn.outgoing[index2].type == 'ASF' and \
                           pn.outgoing[index2].toNode == n.name:
                            pn.outgoing[index2].type = 'ASF2'
                    changes = True
            if elsen is not None and len(En.outgoing) == 1 and \
               En.outgoing[0].toNode == elsen.outgoing[0].toNode:
                if Tn.code == '': Tn.code = 'pass\n'
                Tn.code = 'try:\n' + indentText(Tn.code, 1)
                if elsen.code == '': elsen.code = 'pass\n'
                elsen.code = 'else:\n' + indentText(elsen.code, 1)
                self.removeEdge(n, En)
                self.removeEdge(En, self.nodes[En.outgoing[0].toNode])
                self.removeEdge(Tn, elsen)
                dummyname = elsen.incoming[0].fromNode
                self.removeEdge(self.nodes[dummyname], elsen)
                del self.nodes[dummyname]
                self.addEdge(Tn, En)
                self.addEdge(En, elsen)
                changes = True
            elif elsen is None and len(En.outgoing) == 1 and \
                 En.outgoing[0].toNode == Tn.outgoing[0].toNode:
                latch = self.nodes[En.outgoing[0].toNode]
                if Tn.code == '': Tn.code = 'pass\n'
                Tn.code = 'try:\n' + indentText(Tn.code, 1)
                self.removeEdge(n, En)
                self.removeEdge(Tn, latch)
                for index in xrange(len(latch.incoming)):
                    if latch.incoming[index].type == 'AE':
                        dummyname = latch.incoming[index].fromNode
                        self.removeEdge(self.nodes[dummyname], latch)
                        del self.nodes[dummyname]
                        break
                self.addEdge(Tn, En)
                changes = True
        return changes

    def structureSingleFinally(self, n):
        '''
        @return: True, if finally was structured, False otherwise.

        '''
        changes = False
        (ASFe, ASF2e, finallye) = self.findASFASF2finallyEdge(n)
        if ASFe is not None:
            # it is a try-finally case
            ASFn = self.nodes[ASFe.toNode]
            finallyn = self.nodes[finallye.toNode]
            # check if everything is structured...
            if len(ASFn.outgoing) == 1 and \
               ASFn.outgoing[0].toNode == finallyn.name and \
               len(finallyn.outgoing) == 1 and \
               finallyn.outgoing[0].type == 'AE':
                if ASFn.code == '':
                    ASFn.code = 'pass\n'
                ASFn.code = 'try:\n' + indentText(ASFn.code, 1)
                if finallyn.code == '':
                    finallyn.code = 'pass\n'
                finallyn.code = 'finally:\n' + indentText(finallyn.code, 1)
                self.removeEdge(n, finallyn)
                latch = self.nodes[finallyn.outgoing[0].toNode]
                self.removeEdge(finallyn, latch) # remove AE
                self.addEdge(finallyn, latch)
                changes = True
        elif ASF2e is not None:
            # it is a try-except-(else)-finally case
            ASFn = self.nodes[ASF2e.toNode]
            finallyn = self.nodes[finallye.toNode]
            # check if everything is structured...
            # TODO: remove copypaste
            if len(ASFn.outgoing) == 1 and \
               ASFn.outgoing[0].toNode == finallyn.name and \
               len(finallyn.outgoing) == 1 and \
               finallyn.outgoing[0].type == 'AE':
                if finallyn.code == '':
                    finallyn.code = 'pass\n'
                finallyn.code = 'finally:\n' + indentText(finallyn.code, 1)
                self.removeEdge(n, finallyn)
                latch = self.nodes[finallyn.outgoing[0].toNode]
                self.removeEdge(finallyn, latch) # remove AE
                self.addEdge(finallyn, latch)
                changes = True
        return changes

    def simplifyAllCompound(self):
        '''
        Structures all compound statements (if/else, for, while, try/except).

        '''
        # TODO: test `if a is not in b' and such...
        # TODO: elif
        self.extra = []
        # for drawing
        self.newDebugDrawIteration('simplifyAllCompound')
        self.doDebugDraw()

        changes = True
        while changes:
            changes = False
            pnodes = self.postorder()
            
            for nname in pnodes:
                n = self.nodes[nname]
                if n.conditional:
                    changes = self.structureSingleConditional(n) or changes
                elif n.loop:
                    changes = self.structureSingleLoop(n) or changes
                elif n.exceptNode:
                    changes = self.structureSingleExcept(n) or changes
                elif n.finallyNode:
                    changes = self.structureSingleFinally(n) or changes
            if changes:
                self.doDebugDraw()
   
            changes = self.simplifyConsecutive() or changes
         
            self.newDebugDrawIteration('simplifyAllCompound')

    def simplifyConsecutive(self, verbose=0):
        '''
        Simplify consecutive nodes.

        '''
        nodes = sorted(self.nodes.keys())

        self.newDebugDrawIteration('simplifyConsecutive')
        self.doDebugDraw()

        changes = False

        for nname in nodes:
            if nname not in self.nodes: continue
            n = self.nodes[nname]
            # don't simplify if edge is After Exception edge (AE)
            
            if verbose:
                print self.extra
                print "n: %s"%(n)
                try:
                    print "n.outgoing: %s (%d)"%(n.outgoing[0],len(n.outgoing))
                except:
                    print "n.outgoing: []"
                try:
                    print "og tonode : %s"%(n.outgoing[0].toNode)
                except:
                    print "og tonode: []"
                try:
                    print "tn incomming: %s (%d)"%(self.nodes[n.outgoing[0].toNode].incoming, len(self.nodes[n.outgoing[0].toNode].incoming))
                except:
                    print "tn incomming: %s"%([])
                
            if len(n.outgoing) == 1 and \
               len(self.nodes[n.outgoing[0].toNode].incoming) == 1 \
               and n.outgoing[0].type != 'AE':

                c = self.nodes[n.outgoing[0].toNode]
                code = n.code + c.code
                nn = node(n.name, n.incoming, c.outgoing,
                          conditional=c.conditional, code=code,
                          condition=c.condition, offset=n.offset)
                self.nodes[nname] = nn
                self.updateEdges(c.name, n.name)
                del self.nodes[c.name]
                changes = True

                self.doDebugDraw()
        return changes

    def DFADecompile(self, dc):
        '''
        Decompiles code in all basic blocks, but doesn't do any structuring.

        @param dc: decompiler.

        '''
        import copy
        visited = set()
        DFAStack = [(self.root, [])]
        while len(DFAStack):
            (n, DecompileStack) = DFAStack.pop()
            if n not in visited:
                visited.add(n)
                res = dc.codeDecompile(self.nodes[n].offset,
                                       self.nodes[n].length,
                                       stack=DecompileStack,
                                       mode='conditional')
                (self.nodes[n].code, self.nodes[n].condition) = res
                for e in self.nodes[n].outgoing:
                    DFAStack.append((e.toNode, copy.deepcopy(DecompileStack)))

    def savePythonGraph(self, filename):
        '''
        Saves CFG as a png image by means of graphviz.

        @param filename: CFG will be saved to "filename.png"

        '''
        try:
            import graph
            import gv
        except ImportError:
            print '# Err: no modules for drawing graphs found... try:'
            print '#> sudo apt-get install python-setuptools ' \
                                                   '# needed for the next line'
            print '#> sudo easy_install python-graph '\
                                           '# This actually installs the thing'
            print '#> sudo apt-get install libgv-python ' \
                                             '# for graphviz in python support'
            print '#> sudo apt-get install python-pydot # for pydot'
            return None
        pattern1 = re.compile(r'\n')
        pattern2 = re.compile(r'\"')
        gr = graph.digraph()
        for n in self.nodes:
            if self.nodes[n].code != '':
                if self.nodes[n].condition is not None:
                    txt = re.sub(pattern1, r'\\l', self.nodes[n].code + \
                          '\n\n' + str(self.nodes[n].condition))
                    txt = re.sub(pattern2, r'\\"', txt)
                    gr.add_node(n, [('label', '"' + txt + '"')])
                    #print '1:::'
                    #print txt
                else:
                    txt = re.sub(pattern1, r'\\l', self.nodes[n].code)
                    txt = re.sub(pattern2, r'\\"', txt)
                    gr.add_node(n, [('label', '"' + txt + '"')])
                    #print '2:::'
                    #print txt
            else:
                txt = re.sub(pattern1, r'\\l', str(self.nodes[n].condition))
                txt = re.sub(pattern2, r'\\"', txt)
                gr.add_node(n, [('label', '"' + txt + '"')])
            if not self.nodes[n].conditional:
                gr.add_node_attribute(n, ('shape', 'box'))
        for n in self.nodes:
            for e in self.nodes[n].outgoing:
                gr.add_edge(n, e.toNode, label=e.type)
        dot = gr.write(fmt='dot')
        #print '>>>>>'
        #print dot
        #print '<<<<<'
        gvv = gv.readstring(dot)
        gv.layout(gvv, 'dot')
        gv.render(gvv, 'png', str(filename) + '.png')


def readGraph(filename):
    '''
    Reads CFG from specified file. Deprecated.

    @param filename: name of the file, from which to read from.

    '''
    f = open(filename, 'r')
    s = f.readline()
    nodes = {}
    root = None
    while s != '':
        try:
            filt = lambda x: x != ''
            a = s.rstrip('\r\n').split(':')
            b = a[1].split(';')
            c = filter(filt, b[0].split(','))
            d = filter(filt, b[1].split(','))
            c = [x for x in c if x != '']
            nodes[a[0]] = node(a[0], c, d)
            if root is None: root = a[0]
        except: pass
        s = f.readline()
    f.close()
    return graph(root, nodes)

def readExGraph(filename):
    '''
    Reads CFG from specified file. Deprecated.

    @param filename: name of the file, from which to read from.

    '''
    p1 = re.compile(r'(\d+)\((.*?)\)')
    p2 = re.compile(r'(\d+)\[(.*?)\]')

    def procTF(arr):
        for x in range(len(arr)):
            m1 = p1.search(arr[x])
            if m1 is not None:
                arr[x] = (m1.group(1), m1.group(2))
            else:
                arr[x] = (arr[x], 'o')
        return arr

    def procB(s):
        m1 = p1.search(s)
        if m1 is not None:
            return (m1.group(1), m1.group(2), True) # conditional only
        m2 = p2.search(s)
        if m2 is not None:
            return (m2.group(1), m2.group(2), False) # complex node
        return (s, '', False)

    f = open(filename, 'r')
    s = f.readline()
    nodes = {}
    root = None
    while s != '':
        try:
            filt = lambda x: x != ''
            a = s.rstrip('\r\n').split(':')
            b = a[1].split(';')
            i = []
            o = []
            n = procB(a[0])
            for x in filter(filt, b[0].split(',')):
                i.append(edge(x, n[0]))
            for (x, t) in procTF(filter(filt, b[1].split(','))):
                o.append(edge(n[0], x, t))
            nodes[n[0]] = node(n[0], i, o, conditional=n[2], code=n[1])
            if root is None: root = n[0]
        except: pass
        s = f.readline()
    f.close()
    return graph(root, nodes)

def getGraphFromCodeBlocks(cb, debugDraw=False):
    '''
    Builds CFG from codeblocks.

    @param cb: codeblocks (see L{CodeBlocks}).
    @param debugDraw:
        save intermediate CFGs as images while processing or not.

    '''
    truthTable = {
        # TODO: recheck this truthTable
        'for'     : 'for',
        'AF'      : 'AF',
        'loop'    : 'loop',
        'AL'      : 'AL',
        'DEAD'    : 'DEAD',
        'try'     : 'try',
        'except'  : 'except',
        'ASF'     : 'ASF',
        'finally' : 'finally',
        'AE'      : 'AE',

        'JA'      : 'JA',

        'JF'      : '',

        'JIF'     : 'f',
        'NJIF'    : 't',
        'JIT'     : 't',
        'NJIT'    : 'f'
    }
    cbs = sorted(cb.blocks.keys())
    root = cb.root
    nodes = {}
    # TODO: recheck, optimize, sorted is not necessary??
    for index in xrange(len(cbs)):
        toNode = cbs[index]
        if index < len(cbs) - 1:
            nodes[toNode] = node(toNode, [], [], conditional=False,
                                 code=str(toNode), offset=toNode,
                                 length=cbs[index+1]-toNode)
        else:
            nodes[toNode] = node(toNode, [], [], conditional=False,
                                 code=str(toNode), offset=toNode, length=0)
    for toNode in cbs:
        for ref in cb.blocks[toNode]:
            dbgprint(str(toNode) + ': ' + str(ref))
            type = truthTable[ref.name]
            if type in ('t', 'f'):
                nodes[ref.blockxref].conditional = True
            elif type in ('loop', 'AL'):
                nodes[ref.blockxref].loop = True
            elif type in ('for', 'AF'):
                nodes[ref.blockxref].forloop = True
            elif type in ('try', 'except'):
                nodes[ref.blockxref].exceptNode = True
            elif type in ('finally', 'ASF'):
                nodes[ref.blockxref].finallyNode = True
            nodes[toNode].incoming.append(edge(ref.blockxref, toNode, type))
            nodes[ref.blockxref].outgoing.append(edge(ref.blockxref,
                                                      toNode, type))
    for i in xrange(len(cbs)-1):
        if len(nodes[cbs[i]].outgoing) == 0:
            nodes[cbs[i]].outgoing.append(edge(cbs[i], cbs[i+1], ''))
            nodes[cbs[i+1]].incoming.append(edge(cbs[i], cbs[i+1], ''))
    return graph(root, nodes, debugDraw)

if __name__ == '__main__':
    g = readExGraph('input4.txt')
    print g
    #print g.postorder()
    #print g.intervals()
    if False:
        g.mergeComplexNodes('3', '4', 0)
        print g
        g.mergeComplexNodes('1', '2', 0)
        print g
        g.mergeComplexNodes('1&2', '3&4', 1)
        print g
        print g.postorder()
    g.simplifyComplexIFs()
    print g
