from syndicate.commons.oop.patterns import (
    InterchangeableReference, RetainedReference
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


if __name__ == '__main__':
    unittest.main()
