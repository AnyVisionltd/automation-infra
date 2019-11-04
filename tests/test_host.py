
def _disabled_test_1(host):
    assert host.ip == '0.0.0.0'
    contents = host.Connection.get_contents('/tmp/f1.txt')
    assert contents == b's is a tew\nawetoawefjaw\nafwefoj\n'
    assert True