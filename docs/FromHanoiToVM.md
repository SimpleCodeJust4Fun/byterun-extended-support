# 从非递归汉诺塔到Python虚拟机
项目总结文档，用于讲好这个项目的故事
## 非递归汉诺塔

我在上jyy老师的OS课时，对这个例子印象非常深刻：

非递归汉诺塔的实现

```
class Element:
    def __init__(self, n, _from, _to, _via):
        self.n = n
        self._from = _from
        self._to = _to
        self._via = _via      
      
def hanoi_non_recursive(n, _from, _to, _via):
    stack = []
    stack.append(Element(n, _from, _to, _via))
    cnt = 0
    while stack:
        cur = stack.pop()
        if cur.n == 1:
            print(cur._from, "->",cur._to)
            cnt += 1
        else:
            stack.append(Element(cur.n - 1, _via, _to, _from))
            stack.append(Element(1, _from, _to, _via))
            stack.append(Element(cur.n - 1, _from, _via, _to))
    return cnt
print(hanoi_non_recursive(10, '0', '2', '1'))
```

前段时间面知乎，遇到了要求非递归实现树的遍历的需求，联想到应该也可以用非递归汉诺塔的形式，因此重新琢磨了这个知识。仿照这个思路，可以写出一个通用的非递归树遍历，满足三种遍历顺序：

```
# main.py
class Element:
    def __init__(self, node, cmd):
        self.node = node
        self.cmd = cmd
          
def travelsal_non_recursive(node):
    if not node:
        return
    cmd = 'go'
    stack = [Element(node, cmd)]
    while stack:
        cur = stack.pop()
        if cur.cmd == 'print':
            print(cur.node.val)
        else:
            if cur.node.right:
                stack.append(Element(cur.node.right, 'go'))
            if cur.node.left:   
                stack.append(Element(cur.node.left, 'go'))
            stack.append(Element(cur.node, 'print'))
```

曾经我是从《代码随想录》那里学的两种树的非递归遍历：

```
# 中序遍历-迭代-LC94_二叉树的中序遍历
class Solution:
    def inorderTraversal(self, root: TreeNode) -> List[int]:
        if not root:
            return []
        stack = []  # 不能提前将root结点加入stack中
        result = []
        cur = root
        while cur or stack:
            # 先迭代访问最底层的左子树结点
            if cur:   
                stack.append(cur)
                cur = cur.left	
            # 到达最左结点后处理栈顶结点  
            else:	
                cur = stack.pop()
                result.append(cur.val)
                # 取栈顶元素右结点
                cur = cur.right
        return result

# 前序遍历-迭代-LC144_二叉树的前序遍历
class Solution:
    def preorderTraversal(self, root: TreeNode) -> List[int]:
        # 根结点为空则返回空列表
        if not root:
            return []
        stack = [root]
        result = []
        while stack:
            node = stack.pop()
            # 中结点先处理
            result.append(node.val)
            # 右孩子先入栈
            if node.right:
                stack.append(node.right)
            # 左孩子后入栈
            if node.left:
                stack.append(node.left)
        return result
```

思路很诡异，形式上也不统一，路径是以树的结点为视角去看的，很不直观，这说明代码并没有找到这个问题的本质。最直观的非递归遍历实际上就是自己实现函数调用（以支持递归写法）。相比起来，《代码随想录》那种非递归就是堆砌无用技巧的初等方法；而实现函数调用是普通而典型的高等方法。代码随想录的方法形式上不统一，细节多，非常像高中数学考试中，由于考纲限制不能教授高等知识，因此只能限制在初等世界里。往往学生会堆积很多无用的初等技巧，来解一些看似困难的问题（其实这些问题只是高等内容中的基础典型案例）。我们应当做的是找到正确的、普适的方法，帮助我们理解问题的本质。

上述代码其实就是一个简单的虚拟机，它模拟了函数调用中的栈

栈帧是由编译器维护的，而不是操作系统

- 栈帧也叫过程活动记录，是编译器用来实现过程/函数调用的一种数据结构。简言之，栈帧就是利用EBP（栈帧指针，请注意不是ESP）寄存器访问局部变量、参数、函数返回地址等的手段

其实在实现函数调用上， 编译型语言和虚拟机类解释型语言没有本质区别，前者使用汇编语言的基础语法，对内存和寄存器进行操作，形成了一个看起来像栈的东西；虚拟机类解释型语言就更好理解了，是在A语言里实现了虚拟机，这个虚拟机拥有一个栈的数据结构，并且能够合理地调用栈，以实现函数调用，就像这里非递归汉诺塔的例子一样。

![Alt text](image/%E6%A0%88%E7%9A%84%E7%89%A9%E7%90%86%E6%9C%AC%E8%B4%A8.png)

疑问：生成器的栈帧是什么原理？生成器为什么能保留其运行状态？
省流：Python解释器进程有自己的堆区和栈区，Python代码的栈帧在解释器进程的堆区，因此可以持久存在，不会受压栈影响。https://zhuanlan.zhihu.com/p/584753367
其实这里想不清楚，是由于把解释器进程（虚拟机）和运行在虚拟机上的Python代码弄混了。

结构其实是这样的：
一个物理意义上的计算机，用自己的内存支持着一个普普通通的进程：Python虚拟机。这个进程有一个特殊的本领，它可以在自己的内存的堆空间上，创造出一个栩栩如生的套娃世界（相当于在Minecraft里面玩Minecraft），在这个套娃世界里面，py代码被编译为字节码，然后一条一条地解释执行。这些字节码看起来就像真的运行在一个拥有堆和栈的完整计算机系统上，但是它们其实是Minecraft里的Minecra ft。

1. 一台windows电脑上有两个进程：

- 一个叫做Python虚拟机的普通进程。功能：用内存（堆和栈）和内存地址上的值创造虚拟世界
  - py虚拟机的物理栈（支持虚拟机的函数调用）：
  - py虚拟机的物理堆（某一段堆内存上，new了一大堆东西来创造虚拟世界）：
    - 解释执行的py代码的虚拟栈
    - 解释执行的py代码的虚拟堆
- 一个叫做Minecraft的普通进程。功能：用三维空间和三维坐标上的方块创造虚拟世界
  - Minecraft世界里的一块超平坦空地（某一块超平坦空地上，用红石电路和方块建造的电脑里运行着二维Minecraft）
    - 虚拟Minecraft的超平坦空地
      - ......

因此，在Python解释器（虚拟机）进程的视角中：什么狗屁生成器栈帧，你不过是我源码里的一个class Frame的对象，被我new在堆空间里，我只是做了个看起来像栈的class Stack让她陪你玩玩，让你感觉自己能被压栈出栈。但在我的视角里，我就像操作任何普通对象一样操作你。

## Python虚拟机

ByteRun项目
非常NB的解析博文：
https://zhuanlan.zhihu.com/p/481884570