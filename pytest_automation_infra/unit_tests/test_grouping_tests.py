from automation_infra.utils.grouping_tests import TestAndRequirements, group_tests


def test_grouping_tests_with_one_host():
    test1 = TestAndRequirements({"host" : {"cpu" : 10 , "gpu" : 1}},"test1" )
    test2 = TestAndRequirements({"host" : {"cpu" : 8 , "gpu" : 1}},"test2")
    test3 = TestAndRequirements({"host" : {"cpu" : 10 , "gpu" : 1}},"test3" )
    test4 = TestAndRequirements({"host" : { "gpu" : 1,"cpu":10}},"test4" )

    group_tests_results = group_tests([test1, test2, test3,test4])

    assert len(group_tests_results) == 2
    assert len(group_tests_results[0].tests) == 3
    assert len(set(group_tests_results[0].tests).intersection(["test1","test3","test4"])) == 3
    assert "test2" in group_tests_results[1].tests
    assert len(group_tests_results[1].tests) == 1


def test_grouping_tests_with_multiple_hosts_len():
    test1 = TestAndRequirements({"host1" : {"cpu" : 11 , "gpu" : 1 },"host2" : {"cpu" : 10 , "gpu" : 1}},"test1" )
    test2 = TestAndRequirements({"host1" : {"cpu" : 10 , "gpu" : 1 }, "host2" : {"cpu" : 10 , "gpu" : 1}},"test2" )
    test3 = TestAndRequirements({"host1" : {"cpu" : 10 , "gpu" : 1 },"host2" : {"cpu" : 11 , "gpu" : 1}},"test3" )
    test4 = TestAndRequirements({"host" : { "gpu" : 1,"cpu":10}},"test4" )

    group_tests_results = group_tests([test1, test2, test3,test4])
    assert len(group_tests_results) == 3
    assert len(group_tests_results[0].tests) == 2
    assert len(set(group_tests_results[0].tests).intersection(["test1","test3"])) == 2

    assert len(group_tests_results[1].tests) == 1
    assert "test2" in group_tests_results[1].tests

    assert len(group_tests_results[2].tests) == 1
    assert "test4" in group_tests_results[2].tests

