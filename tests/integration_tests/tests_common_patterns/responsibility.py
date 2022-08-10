from syndicate.commons.oop.patterns import (
    IResponsibilityNode, BlackBoxResponsibilityNode,
    CurriedFunctionBuilder, IterativeFunctionBuilder,
    ResponsibilityNodeBuilder, BlackBoxNodeResponsibilityBuilder,
    DetachedResponsibilityNodeRoutingBuilder,
    RetainedReference, OneToOneRelation,
    PriorityBasedSource, QueueStore,
)

from syndicate.commons.oop.complements import (
    route_node
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
        self.builder = BlackBoxNodeResponsibilityBuilder()
        self.node = BlackBoxResponsibilityNode()
        self.currying = CurriedFunctionBuilder()
        self.iteration = IterativeFunctionBuilder()
        self._sample = lambda s, n: sample(range(n), randint(s, n-1))


    def test_curring_based_computation(self):
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

    def test_iterative_computation(self):
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

        source = PriorityBasedSource()
        source.store = QueueStore()
        self.iteration.attach(source)

        self.builder.attach(self.iteration)
        self.builder.attach(addition)
        self.builder.attach(product)
        node = self.builder.product

        for each in (addition, product):
            sequence = self._sample(2, 10)
            self.assertEqual(
                node.handle(sequence), each(sequence)
            )


class DetachedResponsibilityNodeRoutingProductionTest(BuilderProductionTest):

    def setUp(self) -> None:
        self.node = BlackBoxResponsibilityNode()
        self.node.relation = OneToOneRelation()
        self.builder = DetachedResponsibilityNodeRoutingBuilder()
        self.builder.attach(CurriedFunctionBuilder())

        self.node_builder = BlackBoxNodeResponsibilityBuilder()
        self.iteration = IterativeFunctionBuilder()

        source = PriorityBasedSource()
        source.store = QueueStore()
        self.iteration.attach(source)

        self._sample = lambda s, n: sample(range(n), randint(s, n-1))

    def test_boolean_based_routing(self):
        """
        Tests routing-on-demand behaviour of a black-box responsibility node,
        based on a boolean determinant.
        Given example - node must continue executing itself, producing
        data := data * 2, until the output reaches a threshold of random `k`,
        given that initial `data` value is in range [1; k].
        """
        node = self.node
        node.relation.reference = RetainedReference()

        # Assigns a simple `product of two` function to the box
        node.box = lambda data: data*2

        # Establishes default routing to itself
        route_node(node, node)

        self.builder.attach(self.node)

        k = randint(0, 100)
        b = randint(1, k-1)

        # Attaching a threshold function as a boolean determinant
        self.builder.attach(lambda data: data < k)

        # Abstains from attaching a target, compelling
        # routing to None, thus returning the value

        node = self.builder.product

        output = node.handle(b)

        # Evaluating the excepted output
        expected = b
        while expected < k:
            expected *= 2

        self.assertEqual(output, expected)


    def test_exception_based_routing(self):
        """
        Tests routing-on-demand behaviour of a black-box responsibility node,
        based on a exception determinant.
        Given example - node must continue executing itself, iteratively
        invoking new derived function, until the source has been exhausted.
        """

        node = self.node
        node.relation.reference = RetainedReference()

        # Assigns a `k` functions to an iterative function builder
        k = randint(0, 100)
        functions = []
        for each in range(k):
            i = randint(0, 100)
            functions.append(lambda data: data + i)
            self.iteration.attach(functions[-1])

        # Attaches a derive-based function to a box
        node.box = self.iteration.product

        # Establishes default routing to itself
        route_node(node, node)

        self.builder.attach(self.node)

        # Attaching the StopIteration as a determinant
        self.builder.attach(StopIteration())

        # Abstains from attaching a target, compelling
        # routing to None, thus returning the value

        node = self.builder.product

        b = randint(0, 100)

        output = node.handle(b)

        # Evaluating the excepted output
        expected = b
        for each in functions:
            expected = each(expected)

        self.assertEqual(output, expected)


if __name__ == '__main__':
    unittest.main()
