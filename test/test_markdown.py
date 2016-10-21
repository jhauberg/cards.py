# coding=utf-8

import unittest

from cards.markdown import markdown


class MarkdownTest(unittest.TestCase):
    def test_markdown(self):
        # strong
        self.assertEqual(markdown('**strong**'), '<strong>strong</strong>')
        self.assertEqual(markdown('**strong word**'), '<strong>strong word</strong>')
        self.assertEqual(markdown(' **strong**'), ' <strong>strong</strong>')
        #self.assertEqual(markdown('** strong**'), '** strong**') # on github this is the result
        self.assertEqual(markdown('** strong**'), '<strong> strong</strong>')
        self.assertEqual(markdown('** strong **'), '<strong> strong </strong>')
        self.assertEqual(markdown('**strong** '), '<strong>strong</strong> ')
        self.assertEqual(markdown(' **strong** '), ' <strong>strong</strong> ')

        self.assertEqual(markdown('__strong__'), '<strong>strong</strong>')
        self.assertEqual(markdown(' __strong__'), ' <strong>strong</strong>')
        #self.assertEqual(markdown('__ strong__'), '__ strong__') # on github this is the result
        self.assertEqual(markdown('__ strong__'), '<strong> strong</strong>')
        self.assertEqual(markdown('__ strong __'), '<strong> strong </strong>')
        self.assertEqual(markdown('__strong__ '), '<strong>strong</strong> ')
        self.assertEqual(markdown(' __strong__ '), ' <strong>strong</strong> ')
        self.assertEqual(markdown('(__strong__)'), '(<strong>strong</strong>)')

        # todo: these are weird- what would we expect?
        # self.assertEqual(markdown('****'), '<em>*</em>*') # this works out, but probably not what you'd want
        # self.assertEqual(markdown('____'), '<em>_</em>_') # on github it becomes a horizontal ruler
        # not sure if these should be as shown
        # self.assertEqual(markdown('****'), '****')
        # self.assertEqual(markdown('____'), '____')
        # self.assertEqual(markdown('_____'), '_____')
        self.assertEqual(markdown('** **'), '<strong> </strong>')
        self.assertEqual(markdown('__ __'), '<strong> </strong>')

        # emphasis
        self.assertEqual(markdown('*emphasis*'), '<em>emphasis</em>')
        self.assertEqual(markdown('*emphasized word*'), '<em>emphasized word</em>')
        self.assertEqual(markdown(' *emphasis*'), ' <em>emphasis</em>')
        #self.assertEqual(markdown('* emphasis*'), '* emphasis*') # on github this is the result
        self.assertEqual(markdown('* emphasis*'), '<em> emphasis</em>')
        self.assertEqual(markdown('*emphasis* '), '<em>emphasis</em> ')
        self.assertEqual(markdown(' *emphasis* '), ' <em>emphasis</em> ')

        self.assertEqual(markdown('_emphasis_'), '<em>emphasis</em>')
        self.assertEqual(markdown(' _emphasis_'), ' <em>emphasis</em>')
        #self.assertEqual(markdown('_ emphasis_'), '_ emphasis_') # on github this is the result
        self.assertEqual(markdown('_ emphasis_'), '<em> emphasis</em>')
        self.assertEqual(markdown('_ emphasis _'), '<em> emphasis </em>')
        self.assertEqual(markdown('_emphasis_ '), '<em>emphasis</em> ')
        self.assertEqual(markdown(' _emphasis_ '), ' <em>emphasis</em> ')

        self.assertEqual(markdown('(_emphasis_)'), '(<em>emphasis</em>)')
        self.assertEqual(markdown('no_emphasis_'), 'no_emphasis_')

        self.assertEqual(markdown('\*emphasis*'), '*emphasis*')

        # super
        self.assertEqual(markdown('super^this'), 'super<sup>this</sup>')
        self.assertEqual(markdown('super^this not^'), 'super<sup>this</sup> not^')
        self.assertEqual(markdown('super^this^not_this'), 'super<sup>this^not_this</sup>')
        self.assertEqual(markdown('^this'), '<sup>this</sup>')
        self.assertEqual(markdown('not^'), 'not^')

        # inserted
        self.assertEqual(markdown('++inserted++'), '<ins>inserted</ins>')

        # deleted
        self.assertEqual(markdown('~~deleted~~'), '<del>deleted</del>')

        # break line
        self.assertEqual(markdown('  '), '<br />')
        self.assertEqual(markdown('    '), '<br /><br />')
        self.assertEqual(markdown('one  break'), 'one<br />break')
        self.assertEqual(markdown('two    breaks'), 'two<br /><br />breaks')
        self.assertEqual(markdown('two   breaks'), 'two<br /><br />breaks')
        self.assertEqual(markdown('three      breaks'), 'three<br /><br /><br />breaks')

        # escaping
        self.assertEqual(markdown('\**strong**'), '*<em>strong</em>*')
        self.assertEqual(markdown('\*\*strong**'), '**strong**')

        self.assertEqual(markdown('\__strong__'), '_<em>strong</em>_')
        self.assertEqual(markdown('\_\_strong__'), '__strong__')
