from syndicate.commons.oop.patterns import (
    IResponsibilityNode, BlackBoxResponsibilityNode,
    CurriedFunctionBuilder, ResponsibilityNodeBuilder,
    BlackBoxResponsibilityNodeBuilder,
    OneToOneRelation, RetainedReference,
)

from tests.integration_tests.tests_common_patterns.builder import \
    BuilderProductionTest

from random import randint, sample

import unittest


class NonComputableResponsibilityNodeProductionTest(BuilderProductionTest):

    def setUp(self) -> None:
        self.builder = ResponsibilityNodeBuilder()

    def test_computational_absence(self):
        """
        Test non-computational aspect of the builder, by providing
        a payload, which produces a node with no altering computation
        of any incoming data.
        """
        self.builder.attach(BlackBoxResponsibilityNode())
        self.builder.attach(RetainedReference())
        self.builder.attach(OneToOneRelation())
        node = self.builder.product
        self.assertIsInstance(node, IResponsibilityNode)

        data = randint(0, 10)
        self.assertEqual(node.handle(data), data)


class BlackBoxResponsibilityNodeProductionTest(BuilderProductionTest):

    def setUp(self) -> None:
        self.builder = BlackBoxResponsibilityNodeBuilder()
        self.node = BlackBoxResponsibilityNode()
        self.currying = CurriedFunctionBuilder()
        self._sample = lambda s, n: sample(range(n), randint(s, n-1))


    def test_single_outsourced_computation(self):
        """
        Tests computational behaviour of a black-box responsibility node,
        by producing one with a single computational purpose.
        Given example - sum of provided sequence of integers.
        """
        self.builder.attach(self.node)
        self.builder.attach(self.currying)
        self.builder.attach(lambda *args: sum(*args))
        node = self.builder.product

        sequence = self._sample(2, 10)
        self.assertEqual(node.handle(sequence), sum(sequence))

    def test_queue_outsource_computation(self):
        """
        Tests computational behaviour of a black-box responsibility node,
        by producing one with a queue based computational sources.
        Let there be two black-boxed computations, denoted `f`:
            - sum of provided sequence of integers;
            - product of provided sequence of integers.
        Verifies that each invocation perpetuates cycling through the queue.
        """
        from functools import reduce
        addition = lambda *args: sum(*args)
        product = lambda *args: reduce(lambda a, b: a*b, *args)
        self.builder.attach(self.node)
        self.builder.attach(self.currying)
        self.builder.attach(addition)
        self.builder.attach(product)
        node = self.builder.product

        for each in (addition, product, addition):
            sequence = self._sample(2, 10)
            self.assertEqual(
                node.handle(sequence), each(sequence)
            )


if __name__ == '__main__':
    unittest.main()
