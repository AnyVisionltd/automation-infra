import logging
import uuid


def group_tests(tests):
    logging.debug("comparing between all relevant tests")
    results_hash = {}
    results = {}
    for test in tests:
        hashes = "".join(sorted([str(hash(str(sorted(req.items())))) for _, req in test.requirements.items()]))
        if results_hash.get(hashes) is None:
            results_hash[hashes] = test.requirements
        if results.get(hashes) is None:
            results[hashes] = []
        results[hashes].append(test.test)

    logging.debug("grouping between all tests and requirements")
    return [TestsGroupedRequirements(requirements, results[hash_key]) for hash_key, requirements in
            results_hash.items()]


class TestAndRequirements:
    def __init__(self, requirements, test):
        self.requirements = requirements
        self.test = test


class TestsGroupedRequirements:
    def __init__(self, requirements, tests):
        self.id = uuid.uuid4()
        self.requirements = requirements
        self.tests = tests
