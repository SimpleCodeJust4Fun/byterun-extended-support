def replace_globals(f):
    return

def f():
    1 == 2
    2 == 1


def g():
    return 1  # a is in the builtins and set to 2


# g and f have different builtins that both provide ``a``.
f()
g()
print(getattr(f, "__code__"))