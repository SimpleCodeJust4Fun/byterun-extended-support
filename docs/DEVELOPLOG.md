# byteRun支持Python3.10
开发流程记录文档，用于记录攻克每个节点的流程
## 支持第一个语句：数字常量
第一个语句，加载常量，通过 调试可知，py3.10生成的代码对象里面code.co_codes.co_consts是个空的tuple，应当调查它实际上存在哪里了

用py3.10的解释器进行dis，输出的字节码如下：
```shell
>>> def test_basic():
...     13
... 
>>> dis.dis(test_basic)
  2           0 LOAD_CONST               0 (None)
              2 RETURN_VALUE
```
可以看到字节码中没有操作数，合理怀疑常量的存储方式有变化？用了一个绝对不会缓存的大整数来测试，看起来不是因为常量池：

```shell
>>> def test_basic():
...     1111111111111111111111111111111
... 
>>> dis.dis(test_basic)
  2           0 LOAD_CONST               0 (None)
              2 RETURN_VALUE
```

应该是编译器优化，对于凭空输入的常量，根本就不加载，不生成这样的对象，希望看到这部分的实际CPython代码来验证这一点

还真是：
```shell
>>> def test_return_const():
...     return 12
... 
>>> dis.dis(test_return_const)
  2           0 LOAD_CONST               1 (12)
              2 RETURN_VALUE
```


测试a=17这句，发现intArg的索引在code.co_codes.co_consts中会越界，应该是生成索引位置的代码需要更新了
```shell
intArg = byteint(arg[0]) + (byteint(arg[1]) << 8)
```
应该是左移8位这件事不一样了

感觉如果对python的某个语言特性理解不深刻的话，看源码或者尝试在虚拟机里实现它，是一种王道，就像打乒乓球找教练一样，是真正的王道

- 用能通过byterun测试的py2.7测试了常量语句的运行机制，发现2.7也不会生成新的整数对象：
```shell
dis code here
<code object <module> at 000000000370D2B0, file "<tests.test_basic.TestIt.test_constant>", line 1>
  1           0 LOAD_CONST               0 (None)
              3 RETURN_VALUE  
```
而是在
```shell
intArg = byteint(arg[0]) + (byteint(arg[1]) << 8)
```
中，py2.7能够正确地取到intArg为0，从而拿到
```shell
if byteCode in dis.hasconst:
    arg = f.f_code.co_consts[intArg]
```
其中`f.f_code.co_consts=(None,)`的None，高版本时，这个arg会被取成一个五位数整数而越tuple的界


在 Python 2.7 中，字节码解析部分会从字节码中提取参数。具体来说，对于有参数的字节码，它会使用偏移量 f.f_lasti 和左移操作来构建参数。

    以下是 Python 2.7 中 parse_byte_and_args 方法的工作原理：byteCode 通过读取当前偏移量 
    opoffset 处的字节码获得。如果字节码 byteCode 大于或等于 HAVE_ARGUMENT（即具有参数的字节码），
    则继续下面的处理。arg 用于存储参数，它被初始化为 None。如果有参数，接下来的两个字节将被取出，
    f.f_lasti 向前移动 2 个字节。intArg 通过将两个字节进行左移操作来构建一个整数。根据字节码的类型
    （byteCode），参数 arg 将被设置为合适的值。例如，如果字节码 dis.hasconst 中，arg 会设置为常量
    表达式的值。在 Python 2.7 中，字节码解析部分能够正确处理这些情况，从而获得正确的参数值。这样，你
    可以在 dis.hasconst 中正确地获取常量的值。然而，在 Python 3.10 中，字节码解析部分对参数的处理方
    式发生了变化，需要进行一些修改，以适应新的数据结构。


2.7 
```shell
>>> f.f_lasti
1
>>> f.f_code.co_code
'd\x00\x00S'
>>> map(byteint, f.f_code.co_code)
[100, 0, 0, 83]
map(byteint, f.f_code.co_code[f.f_lasti:f.f_lasti+2])
[0, 0]
f.f_code.co_consts
(None,)

>>> def test_const():
...     a = 1
...     b = 3
...     return 2
...

>>> import dis
>>> dis.dis(test_const)
  2           0 LOAD_CONST               1 (1)
              3 STORE_FAST               0 (a)

  3           6 LOAD_CONST               2 (3)
              9 STORE_FAST               1 (b)

  4          12 LOAD_CONST               3 (2)
             15 RETURN_VALUE

             >>> map(ord,test_const.__code__.co_code)
[100, 1, 0, 125, 0, 0, 100, 2, 0, 125, 1, 0, 100, 3, 0, 83]
```
还真是两个参数拼起来的啊

3.10
```shell
f.f_lasti
1

f.f_code.co_code
b'd\x00S\x00'

map(byteint, f.f_code.co_code)
<map object at 0x0000012929A04EB0>

list(f.f_code.co_code)
[100, 0, 83, 0]
```
看来是这个代码对象的f.f_code.co_code组织形式完全不同了：从str变成了bytes，参数的位置也不同了

还真是两个参数拼起来的啊，来自《Python 源码剖析》P151
```
8.3 Python 虚拟机的运行框架 
Python 源码剖析——深度探索动态语言核心技术 
151
 opcode = NEXTOP(); 
 oparg = 0; 
 //如果指令需要参数，获得指令参数
 if (HAS_ARG(opcode)) 
 oparg = NEXTARG(); 
 dispatch_opcode: 
 switch (opcode) { 
 case NOP: 
 goto fast_next_opcode; 
 case LOAD_FAST: 
 …… 
 } 
}
注意，这只是一个极度简化之后的 Python 虚拟机的样子，如果想一睹 Python 虚拟机
的尊容，请参考 ceval.c 中的源码。
在这个执行架构中，对字节码的一步一步地遍历是通过几个宏来实现的：
[PyEval_EvalFrameEx in ceval.c] 
#define INSTR_OFFSET() (int(next_instr - first_instr)) 
#define NEXTOP() (*next_instr++) 
#define NEXTARG() (next_instr += 2, (next_instr[-1]<<8) + next_instr[-2])
```

最新的cPython实现，还有点看不懂是怎么取oparg的：
https://github.com/python/cpython/blob/main/Python/ceval.c


## 支持返回常量的函数
目标是支持这两个语句：
```python
def test_return_constant(self):
    self.assert_ok("""
    def test():
        return 17
    test()
    """)

def test_print(self):
    self.assert_ok("""
        a = 17
        print(a)
    """)
```
其字节码为：
```shell
tests/test_basic.py::TestIt::test_return_constant >>> dis_code(code)
PyDev console: starting.
dis code here
<code object test at 0x0000012C8549B100, file "<tests.test_basic.TestIt.test_return_constant>", line 2>
  3           0 LOAD_CONST               1 (17)
              2 RETURN_VALUE
dis code here
<code object <module> at 0x0000012C8549B260, file "<tests.test_basic.TestIt.test_return_constant>", line 1>
  2           0 LOAD_CONST               0 (<code object test at 0x0000012C8549B100, file "<tests.test_basic.TestIt.test_return_constant>", line 2>)
              2 LOAD_CONST               1 ('test')
              4 MAKE_FUNCTION            0
              6 STORE_NAME               0 (test)
  4           8 LOAD_NAME                0 (test)
             10 CALL_FUNCTION            0
             12 POP_TOP
             14 LOAD_CONST               2 (None)
             16 RETURN_VALUE
Disassembly of <code object test at 0x0000012C8549B100, file "<tests.test_basic.TestIt.test_return_constant>", line 2>:
  3           0 LOAD_CONST               1 (17)
              2 RETURN_VALUE
```

其co_code属性分别为
```shell
>>> list(frame.f_code.co_code)
[100, 1, 83, 0]

>>> list(frame.f_code.co_code)
[100, 0, 100, 1, 132, 0, 90, 0, 101, 0, 131, 0, 1, 0, 100, 2, 83, 0]
```

其中，字节码的顺序可参考Python源Lib下的opcode.py。

test_return_constant会出错，是因为python3.10.13的code object的co_code属性里字节码里面不区分有参数字节码（如125号字节码LOAD_FAST）和无参数字节码（23号字节码POP_TOP），在co_code中都会跟一个默认参数0

从co_code属性可以看到，即使是在官网定义中没有参数的字节码，（如23号字节码POP_TOP和83号字节码RETURN_VALUE），在co_code中都会跟一个默认参数0

原来的项目对于字节码是否有参数是区别对待的，具体是通过`pyvm2.py/parse_byte_and_args`
中的`if byteCode >= dis.HAVE_ARGUMENT:`逻辑来区分，并对co_code做不同的解析来得到参数或者直接跳过。

现在我们对于理论上没有参数的字节码也不能跳过，也需要装模作样地解析一个假参数给它，因此要做的事情有两件：
1. 在`parse_byte_and_args`中只，移除掉掉原来的项目对字节码是否含有参数的区分
2. 在pyvm2的对应字节码的方法中，把原来没有参数的POP_TOP和RETURN_VALUE增加一个默认的参数，如下
```python
def byte_POP_TOP(self, arg):
    self.pop()
```
再运行测试代码，发现通过了

## 支持if-else
### 简单if-else
Python代码：
```python
a = 1
if a == 2:
    print("ok")
else:
    print("not ok")
```
dis字节码
```shell
>>> dis.dis(code)
  2           0 LOAD_CONST               0 (1)
              2 STORE_NAME               0 (a)
  3           4 LOAD_NAME                0 (a)
              6 LOAD_CONST               1 (2)
              8 COMPARE_OP               2 (==)
             10 POP_JUMP_IF_FALSE       12 (to 24)
  4          12 LOAD_NAME                1 (print)
             14 LOAD_CONST               2 ('ok')
             16 CALL_FUNCTION            1
             18 POP_TOP
             20 LOAD_CONST               4 (None)
             22 RETURN_VALUE
  6     >>   24 LOAD_NAME                1 (print)
             26 LOAD_CONST               3 ('not ok')
             28 CALL_FUNCTION            1
             30 POP_TOP
             32 LOAD_CONST               4 (None)
             34 RETURN_VALUE
```
原生字节码：
```shell
list(f.f_code.co_code)
[100, 0, 90, 0, 

101, 0, 100, 1, 107, 2, 114, 12, 

101, 1, 100, 2, 131, 1, 1, 0, 100, 4, 83, 0, 

101, 1, 100, 3, 131, 1, 1, 0, 100, 4, 83, 0]
```
if-else是用指令跳转实现的，因此if条件满足就不跳转，继续执行，否则跳转到else处执行，目前的跳转功能没有实现，不满足if条件时
，不能跳转到else处。涉及到的比较字节码为：107号COMPARE_OP，跳转字节码为114号POP_JUMP_IF_FALSE
经排查，107号COMPARE_OP没有问题。因此只能是跳转指令的问题

官方文档：在 3.10 版更改: 跳转、异常处理和循环指令的参数现在将为指令偏移量而不是字节偏移量。
- https://docs.python.org/zh-cn/3/library/dis.html

### 复杂if-else
Python代码：
```python
def test_thorough_flow_control(self):
    self.assert_ok("""
    a = 1
    if a == 1:
        print("ok")
    else:
        print("not ok")
    if a == 2:
        print("ok")
    else:
        print("not ok")
    """)
```
```shell
  2           0 LOAD_CONST               0 (1)
              2 STORE_NAME               0 (a)
  3           4 LOAD_NAME                0 (a)
              6 LOAD_CONST               0 (1)
              8 COMPARE_OP               2 (==)
             10 POP_JUMP_IF_FALSE       11 (to 22)
  4          12 LOAD_NAME                1 (print)
             14 LOAD_CONST               1 ('ok')
             16 CALL_FUNCTION            1
             18 POP_TOP
             20 JUMP_FORWARD             4 (to 30)
  6     >>   22 LOAD_NAME                1 (print)
             24 LOAD_CONST               2 ('not ok')
             26 CALL_FUNCTION            1
             28 POP_TOP
  7     >>   30 LOAD_NAME                0 (a)
             32 LOAD_CONST               3 (2)
             34 COMPARE_OP               2 (==)
             36 POP_JUMP_IF_FALSE       25 (to 50)
  8          38 LOAD_NAME                1 (print)
             40 LOAD_CONST               1 ('ok')
             42 CALL_FUNCTION            1
             44 POP_TOP
             46 LOAD_CONST               4 (None)
             48 RETURN_VALUE
 10     >>   50 LOAD_NAME                1 (print)
             52 LOAD_CONST               2 ('not ok')
             54 CALL_FUNCTION            1
             56 POP_TOP
             58 LOAD_CONST               4 (None)
             60 RETURN_VALUE

```
```shell
>>> list(f.f_code.co_code)
[100, 0, 90, 0, 

101, 0, 100, 0, 107, 2, 114, 11, 

101, 1, 100, 1, 131, 1, 1, 0, 110, 4, 

101, 1, 100, 2, 131, 1, 1, 0, 

101, 0, 100, 3, 107, 2, 114, 25, 

101, 1, 100, 1, 131, 1, 1, 0, 100, 4, 83, 0, 101, 1, 100, 2, 131, 1, 1, 0, 100, 4, 83, 0]
```

发现比起上一个，多了跳转指令JUMP_FORWARD。查阅两个字节码的机制花了不少功夫，这里chatgpt3.5是很没用的（经查阅，Python3.10发布于2021年10月14日。而GPT3.5的知识库截止日是2021年9月）

POP_JUMP_IF_FALSE跳转的是绝对量，但跳转值从字节数量改成了字节码数量，因此在字节码本身的实现上要乘以2
JUMP_FORWARD是相对跳转，也是从字节数量变成字节码数量，字节码本身实现不改动，而是在`parse_byte_and_args`中
的`elif byteCode in dis.hasjrel`:里乘以2，具体查看commit的代码更新 

## 支持for循环
主角是68号GET_ITER、93号FOR_ITER和113号JUMP_ABSOLUTE
Python源码：
```python
def test_for_loop(self):
    self.assert_ok("""\
        out = ""
        for i in range(5):
            out = out + str(i)
        print(out)
        """)
```
dis字节码：
```shell
tests/test_basic.py::TestIt::test_for_loop >>> dis.dis(code)
PyDev console: starting.
  1           0 LOAD_CONST               0 ('')
              2 STORE_NAME               0 (out)
  2           4 LOAD_NAME                1 (range)
              6 LOAD_CONST               1 (5)
              8 CALL_FUNCTION            1
             10 GET_ITER
        >>   12 FOR_ITER                 8 (to 30)
             14 STORE_NAME               2 (i)
  3          16 LOAD_NAME                0 (out)
             18 LOAD_NAME                3 (str)
             20 LOAD_NAME                2 (i)
             22 CALL_FUNCTION            1
             24 BINARY_ADD
             26 STORE_NAME               0 (out)
             28 JUMP_ABSOLUTE            6 (to 12)
  4     >>   30 LOAD_NAME                4 (print)
             32 LOAD_NAME                0 (out)
             34 CALL_FUNCTION            1
             36 POP_TOP
             38 LOAD_CONST               2 (None)
             40 RETURN_VALUE
```
原生字节码：
```shell
list(frame.f_code.co_code)
[100, 0, 90, 0, 

101, 1, 100, 1, 131, 1, 68, 0, 93, 8, 90, 2, 

101, 0, 101, 3, 101, 2, 131, 1, 23, 0, 90, 0, 113, 6, 101, 4, 101, 0, 131, 1, 1, 0, 100, 2, 83, 0]
```

搞错了，主角只是113号JUMP_ABSOLUTE，修改为跳转字节码而不是字节数即可（跳转距离乘以二）