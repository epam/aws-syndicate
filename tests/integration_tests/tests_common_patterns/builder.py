import unittest

from syndicate.commons.oop.patterns import CurriedFunctionBuilder
from syndicate.commons.oop.complements.builder import produce_filter_function

from random import sample


class BuilderProductionTest(unittest.TestCase):

    def test_product_exception(self):
        """
        Tests whether production raises NotImplementedError,
        given the absence of quintessential instance attributes.
        """
        builder = getattr(self, 'builder', None)
        if builder:
            self.assertRaises(NotImplementedError, lambda: builder.product)


class CurryingProductionTest(BuilderProductionTest):

    def setUp(self) -> None:
        self.builder = CurriedFunctionBuilder()
        self.retrieve = lambda data: data

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

    def test_retrieve_policy(self):
        """
        Tests retrieving/return policy of a curried function, by compelling
        function to return the last element of a sequence.
        """
        self.builder.attach(self.retrieve)
        self.builder.retrieve(lambda data: data[-1])
        function = self.builder.product
        payload = range(10)
        self.assertEqual(function(payload), payload[-1])

    def test_indistinguishability(self):
        """
        Tests congruency of outputs, given out of two curried functions,
        composed respectively by prepending and appending.
        """
        n, k = sample(range(10), 2)
        core = lambda data: data + k
        self.builder.attach(self.retrieve)
        self.builder.pre(core)
        pre = self.builder.product

        self.builder.attach(self.retrieve)
        self.builder.post(core)
        post = self.builder.product

        self.assertEqual(pre(n), post(n))

    def test_persistent_attachment(self):
        """
        Tests attachment to a single function, enforcing bounded commitment.
        """
        n, k = sample(range(10), 2)
        self.builder.attach(lambda data: data+k)
        product = self.builder.product
        self.assertEqual(product(n), n+k)

    def test_deque_attachment(self):
        """
        Tests continues queue-based attachment to functions, which rotate with
        respect to the order.
        Given example of a modular addition provides:
            - attachments:Deque[f[i](data) := data + i], for 0<i<n.
            - constant input equal to 1.
        Therefore, for each execution of a curried function, at some point
        of time denoted `t`, output is congruent to 0 < (t mod n) + 1 < n+1.
        """
        from collections import deque
        from random import randint

        n = randint(2, 20)
        attachments = deque([
            (lambda value: lambda data: data+value)(each)
            for each in range(n)
        ])
        self.builder.attach(attachments)
        product = self.builder.product
        output = [product(1) for _ in range(n+1)]
        expected = [t % n + 1 for t in range(n+1)]
        self.assertEqual(output, expected)


class FilterFunctionProductionTest(unittest.TestCase):

    def setUp(self) -> None:
        self.condition = lambda data: data in range(10)

    def test_tuple_filtering_product(self):
        """
        Tests filtering of an iterative data, based on a sample range condition.
        """
        payload = tuple(range(20))
        function = produce_filter_function(
            self.condition,
            extraction=lambda data: data,
            unwrap=lambda data: data,
            encapsulate=tuple,
        )
        output, expected = function(payload), payload[:10]
        self.assertEqual(output, expected)

    def test_dictionary_filtering_product(self):
        """
        Tests filtering of mapped data, based on a sample range condition.
        """
        from string import ascii_lowercase as letters

        payload = dict(zip(letters[:20], range(20)))

        function = produce_filter_function(
            self.condition,
            unwrap=lambda data: dict.items(data),
            encapsulate=dict,
            extraction=lambda data: data[1]
        )
        output, expected = tuple(function(payload)), tuple(letters[:10])
        self.assertEqual(output, expected)


if __name__ == '__main__':
    unittest.main()