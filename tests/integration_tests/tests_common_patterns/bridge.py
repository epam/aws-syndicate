from syndicate.commons.oop.patterns import (
    InterchangeableReference, RetainedReference, PriorityBasedSource,
    QueueStore
)

from random import randint

import unittest


class ReferenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.interchangeable_reference = InterchangeableReference()
        self.retained_reference = RetainedReference()

    def test_interchangeable_reference(self):
        """
        Tests interchangeable reference, stressing on assignment and removal
        actions.
        """
        sample = object()
        self.interchangeable_reference.commitment = sample
        self.assertIs(
            self.interchangeable_reference.commitment, sample
        )
        del self.interchangeable_reference.commitment
        self.assertIs(
            self.interchangeable_reference.commitment, None
        )

    def test_retained_reference(self):
        """
        Tests retained reference, stressing on ephemeral assignment
        and removal actions.
        """
        persisted, *transient = (object() for _ in range(randint(2, 10)))
        self.retained_reference.commitment = persisted
        self.assertIs(self.retained_reference.commitment, persisted)

        for each in transient:
            self.retained_reference.commitment = each
        expired = [
            self.retained_reference.commitment for _ in range(len(transient))
        ]
        self.assertEqual(expired, transient)
        self.assertIs(self.retained_reference.commitment, persisted)

        del self.retained_reference.commitment
        self.assertIs(self.retained_reference.commitment, None)

class PriorityBasedQueuedSourceTest(unittest.TestCase):
    def setUp(self):
        self.source = PriorityBasedSource()
        self.source.store = QueueStore()

    def test_single_priority_retrieval(self):
        """
        Tests priority based retrieval out of store.
        """
        k = randint(0, 100)
        self.source.put(k)
        self.assertEqual(self.source.get(), k)

    def test_iterative_behaviour(self):
        """
        Tests priority based iterative behaviour of the source.
        """
        n, excepted = randint(0, 100), []
        for _ in range(n):
            k = randint(0, 100)
            excepted.append(k)
            self.source.put(k)
        self.assertEqual(list(iter(self.source.get, None)), excepted)

if __name__ == '__main__':
    unittest.main()
