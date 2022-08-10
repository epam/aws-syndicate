import unittest

from syndicate.commons.oop.patterns import (
    CurriedFunctionBuilder, IterativeFunctionBuilder,
    PriorityBasedSource, QueueStore
)

from syndicate.commons.oop.complements.builder import (
    produce_function, produce_filter_builder
)

from random import sample, randint


class BuilderProductionTest(unittest.TestCase):

    def test_product_exception(self):
        """
        Tests whether production raises NotImplementedError,
        given the absence of quintessential instance attributes.
        """
        builder = getattr(self, 'builder', None)
        if builder:
            self.assertRaises(NotImplementedError, lambda: builder.product)


class FunctionCurringProductionTest(BuilderProductionTest):

    def setUp(self) -> None:
        self.builder = CurriedFunctionBuilder()

    def test_prepending(self):
        """
        Tests currying of a function using the prepending approach.
        Given example provides functional adaptation of input data.
        """
        self.builder.attach(lambda data: data.popitem())
        self.builder.pre(lambda data: dict.fromkeys(data))
        function = self.builder.product
        payload = range(10)
        self.assertEqual(function(payload), (9, None))

    def test_appending(self):
        """
        Tests currying of a function using the appending approach.
        Given example provides functional adaptation of input data.
        """
        self.builder.attach(lambda data: data.popitem())
        self.builder.pre(lambda data: dict.fromkeys(data))
        function = self.builder.product
        payload = range(10)
        self.assertEqual(function(payload), (9, None))


    def test_indistinguishability(self):
        """
        Tests congruency of outputs, given out of two curried functions,
        composed respectively by prepending and appending.
        """
        n, k = sample(range(10), 2)
        core = lambda data: data + k
        self.builder.attach(lambda data: data)
        self.builder.pre(core)
        pre = self.builder.product

        self.builder.attach(lambda data: data)
        self.builder.post(core)
        post = self.builder.product

        self.assertEqual(pre(n), post(n))

    def test_exception_based_condition(self):
        """
        Tests exception based handling of a given curried function.
        Given example provides a function, which handles
        ZeroDivisionError, by returning a message:str.
        """
        self.builder.attach(lambda a, b: a//b)
        message = '{} cannot divide {}.'
        self.builder.condition(ZeroDivisionError(),
                               lambda a, b: message.format(a, b))
        function = self.builder.product
        self.assertEqual(function(1, 0), message.format(1, 0))

    def test_boolean_based_condition(self):
        """
        Tests condition based handling of a given curried function.
        Given example provides a function, which handles
        ZeroDivisionError, by returning a message:str.
        """
        self.builder.attach(lambda a, b: a // b)
        message = '{} cannot divide {}.'
        self.builder.condition(lambda a, b: b != 0,
                               lambda a, b: message.format(a, b))
        function = self.builder.product
        self.assertEqual(function(1, 0), message.format(1, 0))


class IterativeFunctionalProductionTest(BuilderProductionTest):

    def setUp(self) -> None:
        self.builder = IterativeFunctionBuilder()
        self.source = PriorityBasedSource()
        self.source.store = QueueStore()

    def test_unattached_source_exception(self):
        """
        Test exception raising, given an instance of
        attaching a function before a source.
        """
        action = lambda: self.builder.attach(lambda data: data)
        self.assertRaises(NotImplementedError, action)

    def test_iterative_exception(self):
        """
        Tests StopIteration exception rising, given
        a finite source has run out of functions.
        An example of such, may be a source of `n` functions.
        """
        n = randint(0, 20)
        self.builder.attach(self.source)
        for _ in range(n):
            self.builder.attach(lambda *_ : None)
        function = self.builder.product

        _, *_ = map(function, range(n))
        self.assertRaises(StopIteration, function)

    def test_iterative_invocation(self):
        """
        Tests iterative behaviour of deriving a function, out of
        a source, for any new execution.
        """
        functions = (lambda a, b: a+b, lambda a, b: a-b)
        self.builder.attach(self.source)
        for each in functions:
            self.builder.attach(each)
        function = self.builder.product

        excepted, output = [], []
        for each in functions:
            _a, _b = map(lambda _: randint(0, 100), range(2))
            excepted.append(each(_a, _b))
            output.append(function(_a, _b))

        self.assertEqual(output, excepted)



class FilterFunctionProductionTest(unittest.TestCase):

    def setUp(self) -> None:
        self.condition = lambda data: data in range(10)

    def test_tuple_filtering_product(self):
        """
        Tests filtering of an iterative data, based on a sample range condition.
        """
        payload = tuple(range(20))
        function = produce_function(produce_filter_builder(
            self.condition,
            extraction=lambda data: data,
            unwrap=lambda data: data,
            wrap=tuple,
        ))
        output, expected = function(payload), payload[:10]
        self.assertEqual(output, expected)

    def test_dictionary_filtering_product(self):
        """
        Tests filtering of mapped data, based on a sample range condition.
        """
        from string import ascii_lowercase as letters

        payload = dict(zip(letters[:20], range(20)))

        function = produce_function(produce_filter_builder(
            self.condition,
            unwrap=lambda data: dict.items(data),
            wrap=dict,
            extraction=lambda data: data[1]
        ))
        output, expected = tuple(function(payload)), tuple(letters[:10])
        self.assertEqual(output, expected)



if __name__ == '__main__':
    unittest.main()