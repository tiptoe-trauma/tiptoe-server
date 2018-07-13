from average_dict import *
from unittest import TestCase, skip

class AverageDictTests(TestCase):
    
    def test_should_return_same_keys(self):
        input_dict_list = [{'a':0, 'b':[], 'c':'string', 'd': True}]
        output_dict = average_dict(input_dict_list)
        self.assertEqual(input_dict_list[0].keys(), output_dict.keys())

    def test_keys_should_be_same_type(self):
        input_dict_list = [{'a':0, 'b':[], 'c':'string', 'd': True}]
        output_dict = average_dict(input_dict_list)
        input_types = [type(input_dict_list[0][x]) for x in input_dict_list[0].keys()]
        output_types = [type(output_dict[x]) for x in output_dict.keys()]
        self.assertEqual(input_types, output_types)

    def test_fetch_returns_all_values(self):
        dicts = [{'a':2},{'a':2},{'a':4},{'a':4}]
        self.assertEqual(fetch('a', dicts), [2, 2, 4, 4])

    def test_dict_typing(self):
        input_dict_list = [{'a':0, 'b':None, 'c':'string', 'd': None},
                           {'a':0, 'b':[], 'c':None, 'd': True},
                           {'a':None, 'b':[], 'c':'string', 'd': None},
                           {'a':None, 'b':[], 'c':'string', 'd': None}]
        self.assertEqual(dict_typing(input_dict_list),
                {'a':type(0), 'b':type([]), 'c':type('string'), 'd':type(True)})

    def test_dict_typing_with_nones(self):
        input_dict_list = [{'a':None},{'a':1}]
        self.assertEqual(dict_typing(input_dict_list), {'a':type(1)})
        input_dict_list = [{'a':None},{'a':1},{'a':None}]
        self.assertEqual(dict_typing(input_dict_list), {'a':type(1)})

    def test_should_exception_with_differing_types(self):
        input_dicts = [{'a':1},{'a':True}]
        with self.assertRaises(Exception):
            dict_typing(input_dicts)

    def test_averages_integers(self):
        numbers = [2, 2, 4, 4]
        self.assertEqual(average_integer(numbers), 3)
        numbers = [2, 2, 3]
        self.assertEqual(average_integer(numbers), 2)

    def test_average_dict_with_ints(self):
        dicts = [{'a':2},{'a':2},{'a':4},{'a':4}]
        self.assertEqual({'a':3}, average_dict(dicts))

    def test_average_floats(self):
        numbers = [1.0, 1.0, 0.0, 0.0]
        self.assertEqual(.5, average_floats(numbers))
        numbers = [6.0, 1.0, 3.0, 0.0]
        self.assertEqual(2.5, average_floats(numbers))

    def test_average_dict_with_floats(self):
        dicts = [{'a':2.0},{'a':2.0},{'a':4.0},{'a':6.0}]
        self.assertEqual({'a':3.5}, average_dict(dicts))

    def test_average_bools(self):
        bools = [True, True, True, False]
        self.assertEqual(True, average_bools(bools))
        bools = [True, True, False, False]
        self.assertEqual(True, average_bools(bools))
        bools = [False]
        self.assertEqual(False, average_bools(bools))
        bools = [False, True, False, False]
        self.assertEqual(False, average_bools(bools))

    def test_average_dict_with_bools(self):
        dicts = [{'a':True},{'a':True},{'a':False},{'a':True}]
        self.assertEqual({'a':True}, average_dict(dicts))

    def test_average_strings(self):
        strings = ['aa', 'aa', 'b', 'bb']
        self.assertEqual('aa', average_strings(strings))

    def test_average_dict_with_strings(self):
        dicts = [{'a':'aa'},{'a':'aa'},{'a':None},{'a':'b'}]
        self.assertEqual({'a':'aa'}, average_dict(dicts))

    def test_average_list_of_strings(self):
        lists = [['a', 'b'],
                 ['a', 'c'],
                 ['a'],
                 ['d', 'b']]
        self.assertEqual(['a', 'b'], average_string_lists(lists))

    def test_average_dict_with_list_of_strings(self):
        lists = [{'a': ['a', 'b']},
                 {'a': ['a', 'c']},
                 {'a': ['a']},
                 {'a': ['d', 'b']}]
        self.assertEqual({'a':['a', 'b']}, average_dict(lists))
