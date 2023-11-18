byterun虚拟机里面所谓的py3版本，内置的Function object用的还是PY2的那套属性；
真实的python3.3.5，走的是下面那套命名

可以看到，在pyobj.py中，只有
```
class Function(object):
    __slots__ = [
        'func_code', 'func_name', 'func_defaults', 'func_globals',
        'func_locals', 'func_dict', 'func_closure',
        '__name__', '__dict__', '__doc__',
        '_vm', '_func',
    ]
```
这个定义，换句话说，他压根就没有支持PY3里函数对象的那些属性

```python
class Function(object):
    __slots__ = [
        'func_code', 'func_name', 'func_defaults', 'func_globals',
        'func_locals', 'func_dict', 'func_closure',
        '__name__', '__dict__', '__doc__',
        '_vm', '_func',
    ]

    def __init__(self, name, code, globs, defaults, closure, vm):
        self._vm = vm

        # PY3 function attrs
        self.__name__ = name or code.co_name
        self.__defaults__ = tuple(defaults)
        self.func_globals = globs
        self.func_locals = self._vm.frame.f_locals
        self.__code__ = code
        self.__closure__ = closure
```


这样定义并运行Function类的构造函数，但是调试运行时，发现运行self.__defaults__ = tuple(defaults)并不会让self多出一个__name__属性，为什么？

非常奇怪！

看起来__code__属性在受保护的特性中，py3.3.5使用print(getattr(f, "__code__"))是可以拿到一个函数的__code__属性的

但是现在的虚拟机里面没有实现这个东西，虚拟机里的Function拿不到这个

搞定，在类定义和__slot__列表中都要添加这些属性：

在你提供的代码中，你尝试为 Function 类的构造函数中添加 ___code___ 属性，但这个属性实际上没有在该类的 __slots__ 中列出。__slots__ 是一个用于指定类的实例可以包含哪些属性的列表。在Python中，__slots__ 是一种用于限制对象属性的机制，只有列在 __slots__ 中的属性可以被赋值和访问。

因此，如果你希望为 Function 类的实例添加 ___code___ 属性，你需要将它包含在 __slots__ 列表中，就像其他属性一样，如下所示：

python
Copy code
class Function(object):
    __slots__ = [
        'func_code', 'func_name', 'func_defaults', 'func_globals',
        'func_locals', 'func_dict', 'func_closure',
        '__name__', '__dict__', '__doc__',
        '_vm', '_func', '___code___',
    ]

    def __init__(self, name, code, globs, defaults, closure, vm):
        # ... (构造函数的其余部分)
        self.___code___ = code
        # ... (构造函数的其余部分)
一旦你将 ___code___ 添加到 __slots__ 中，你就可以在构造函数中使用它，以确保它被正确创建和初始化。不过，请确保与其他属性一起使用 ___code___ 时没有潜在的冲突，以免引起问题。




