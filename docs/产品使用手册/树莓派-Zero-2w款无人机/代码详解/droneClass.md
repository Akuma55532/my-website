---
sidebar_position: 2
---

# `droneClass.py`

## 1. 文件定位

`droneClass.py` 是整个工程中最底层的飞控通信封装模块。

它的主要职责不是做 ROS 通信，也不是做视觉检测，而是：

- 建立与飞控 TCP 服务端的连接
- 通过 MAVLink 协议收发控制与状态数据
- 缓存飞控当前状态
- 向上层提供解锁、起飞、降落、相对位移、绝对位移等接口

上层节点 `fcu_bridge.py` 会调用这个类，把 ROS topic 转换成真正发往飞控的 MAVLink 命令。

---

## 2. 整体职责概括

从工程结构上看，`droneClass.py` 可以理解为“飞控客户端驱动层”。

它在系统中的位置大致是：

```text
RViz Panel / yolo_detect / aruco_detect
                ↓
           fcu_bridge.py
                ↓
          droneClass.py
                ↓
         TCP + MAVLink
                ↓
               FCU
```

因此，这个文件最值得关注的并不是初始化细节，而是下面三部分：

- 飞控回传数据是怎么被解析并缓存的
- 相对位移命令是怎么转换成目标点的
- 二次开发时哪些位置最容易改，改了会影响什么

---

## 3. 初始化阶段简述

初始化逻辑位于 `droneClass.py` 的开头部分。

这一部分主要完成：

- 创建 TCP socket 并连接飞控
- 构造 `MAVLink` 实例
- 初始化位置、姿态、电池等成员变量
- 设置线程发送锁 `_send_lock`

这部分通常不需要频繁改动，除非后续通信方式从 TCP 改成串口、UDP 或其他接口。  
所以在二次开发里，它不是重点。

---

## 4. 核心数据流

`droneClass.py` 的核心数据流可以概括为两条链：

### 4.1 下行控制链

```text
上层调用 setArm / setTakeoff / setPosition / setGlobalPosition
            ↓
     生成 MAVLink 控制消息
            ↓
      _socket_write() 发送到 TCP
            ↓
              飞控执行
```

### 4.2 上行状态链

```text
飞控通过 TCP 发回 MAVLink 字节流
              ↓
        droneListen() 持续接收
              ↓
        parse_char() 逐字节解析
              ↓
        handleMessage() 分类处理
              ↓
      更新 position / attitude / battery
```

对于技术文档而言，后续最有价值的部分就是 `handleMessage()`、`setPosition()` 和 `setGlobalPosition()`。

---

## 5. 消息接收与状态解析

### 5.1 接收线程 `droneListen()`

函数位置：

- `droneListen()`

这个函数通常由独立线程运行，它持续从 TCP socket 中读取原始字节流，然后把每个字节送进 MAVLink 解析器：

```python
data = self.socket_tcp.recv(1024)
for c in data:
    byte_c = bytes([c])
    msg = self.mav_drone.parse_char(byte_c)
    if msg is not None:
        self.handleMessage(msg)
```

### 5.2 为什么这里值得关注

这一段是后续二次开发里非常常见的改动点，因为只要飞控侧新增了消息类型，或者你想接入更多遥测信息，就一定会继续扩展这条链路。

常见改动方向包括：

- 新增对更多 MAVLink 消息的支持
- 增加日志打印或调试信息
- 对消息异常做更细致的错误处理
- 将消息缓存改为线程安全结构

### 5.3 消息解析 `handleMessage()`

函数位置：

- `handleMessage()`

当前代码只处理了三类消息：

- `MAVLINK_MSG_ID_HEARTBEAT`
- `MAVLINK_MSG_ID_BATTERY_STATUS`
- `MAVLINK_MSG_ID_GLOBAL_VISION_POSITION_ESTIMATE`

#### 1. 心跳消息

```python
if msg_id == MAVLINK_MSG_ID_HEARTBEAT:
    print(f'drone{self.drone_id} heartbeat')
```

当前只做终端打印，没有进一步更新连接状态机。  
如果后续要做更完整的在线监测，这里可以扩展为：

- 记录最近一次心跳时间
- 判断飞控是否超时离线
- 根据模式信息更新 UI

#### 2. 电池状态消息

```python
self.battery_voltage = msg.voltages[1] / 1000.0
self.battery_current = msg.current_battery / 100.0
```

这里的作用是把 MAVLink 原始值转换成更容易使用的工程单位：

- 电压单位转成 `V`
- 电流单位转成 `A`

二次开发时这里常见的改法有：

- 改取 `voltages[0]` 还是 `voltages[1]`
- 加入剩余电量百分比解析
- 对异常值增加范围过滤

#### 3. 视觉定位消息

```python
self.position_x = msg.x / 100.0
self.position_y = msg.y / 100.0
self.position_z = msg.z / 100.0
self.att_roll = msg.roll
self.att_pitch = msg.pitch
self.att_yaw = msg.yaw
```

这是当前工程最关键的状态来源。  
`setPosition()` 和 `setGlobalPosition()` 发送控制命令时，都依赖这里缓存下来的当前位置与姿态。

### 5.4 这一段的二次开发价值

如果后续你要做下面这些功能，基本都会先改这里：

- 从其他 MAVLink 消息获取位置，而不是 `GLOBAL_VISION_POSITION_ESTIMATE`
- 用外部定位源替代当前视觉位置
- 增加速度、航向、飞行模式、卫星数等状态
- 修正坐标单位、坐标系方向或角度定义

所以这部分在二次开发中的优先级很高。

---

## 6. 控制接口概览

当前这个类对上层暴露了这些主要控制接口：

- `setArm()`
- `setDisarm()`
- `setTakeoff()`
- `setLand()`
- `sendHeartbeat()`
- `setPosition(x, y, z, yaw)`
- `setGlobalPosition(x, y, z, yaw)`

其中最值得详细分析的是：

- `setPosition()`：相对位置控制
- `setGlobalPosition()`：绝对位置控制

因为你后续做追踪、手动微调、自动任务，基本都会围绕这两个函数改。

---

## 7. 相对位置控制 `setPosition()`

函数位置：

- `setPosition()`

这个函数的输入语义是：

- `x`：机体系前后方向的相对位移
- `y`：机体系左右方向的相对位移
- `z`：垂直方向的相对位移
- `yaw`：相对偏航增量，若为 `None` 则保持当前偏航

### 7.1 它实际做了什么

这不是一个“直接发速度”的函数，也不是一个“直接发机体系坐标”的函数。  
它的真实逻辑是：

1. 读取当前缓存位置和姿态
2. 将机体系相对位移 `(x, y)` 旋转到全局坐标系
3. 与当前位置相加，得到新的绝对目标点
4. 通过 MAVLink 发送位置目标

### 7.2 关键代码片段：机体系转全局系

```python
global_dx = x * math.cos(self.att_yaw) - y * math.sin(self.att_yaw)
global_dy = x * math.sin(self.att_yaw) + y * math.cos(self.att_yaw)
```

这两行是整个相对控制逻辑的核心。  
它表示：

- `x/y` 输入是相对于机头方向定义的
- 但飞控位置目标往往要在某个固定参考系下表达
- 所以必须结合当前偏航角 `att_yaw` 进行坐标旋转

### 7.3 关键代码片段：构造目标点

```python
self.x = self.position_x + global_dx
self.y = self.position_y + global_dy
self.z = self.position_z + z
```

这里把“相对位移控制”转成了“绝对位置目标”。  
也就是说，这个函数的控制思想是：

- 用户给我一个相对偏移量
- 我帮你换算成新的绝对目标点
- 再把这个目标点交给飞控

### 7.4 关键代码片段：偏航处理

```python
if yaw is None:
    self.yaw = self.att_yaw
else:
    self.yaw = self.att_yaw + yaw
```

这里体现了当前工程对 yaw 的定义：

- `yaw=None`：保持当前朝向
- `yaw` 有值：作为“相对转角”叠加到当前朝向上

这也是二次开发中经常会改的地方。  
例如有些项目不希望传相对 yaw，而是希望传绝对 yaw，这时就会改这里。

### 7.5 关键代码片段：最终发送

```python
self.mav_drone.set_position_target_local_ned_send(...)
```

真正发给飞控的不是原始 `x/y/z`，而是上面算出的 `self.x/self.y/self.z/self.yaw`。

### 7.6 二次开发最常改的内容

这部分是整个文件里最值得详细写的改动点：

#### 1. 修改坐标系定义

当前 `z` 的处理非常直接：

```python
self.z = self.position_z + z
```

但底层用的是 `set_position_target_local_ned_send(...)`，这里很容易出现坐标系语义冲突。  
如果后续发现：

- 上升/下降方向反了
- 下视跟踪的 `z` 行为不符合预期
- 外部定位系与飞控系定义不一致

通常就是从这里开始改。

#### 2. 修改相对控制逻辑

如果后续你不想再采用“当前位置 + 偏移量 = 目标点”的方式，而是想：

- 直接发送速度
- 使用机体系目标
- 引入限幅、死区、低通滤波
- 加入 PID 或更复杂控制器

那么 `setPosition()` 会是最重要的改动点。

#### 3. 修改 yaw 的解释方式

当前 yaw 是相对量。  
如果你想把 `fcu_bridge.py` 或追踪节点里送下来的 yaw 改成绝对角，就需要重构这里的：

```python
self.yaw = self.att_yaw + yaw
```

#### 4. 修改调试输出

当前函数里有明显的调试打印：

```python
print(f'Position_now: ...')
print(f'Position_next: ...')
```

这对于联调很有帮助，但如果后续控制频率高，会刷屏。  
实际工程里常会把它替换成：

- 节流日志
- ROS 日志
- 条件调试开关

---

## 8. 绝对位置控制 `setGlobalPosition()`

函数位置：

- `setGlobalPosition()`

这个函数相比 `setPosition()` 更简单：它不会做坐标旋转，也不会把相对位移转换为绝对目标点，而是直接把传入的 `x/y/z` 当作目标位置。

关键逻辑是：

```python
self.x = x
self.y = y
self.z = z
```

以及：

```python
if yaw is None:
    self.yaw = self.att_yaw
else:
    self.yaw = yaw
```


## 9. 总结

`droneClass.py` 是本工程的飞控通信基础模块，它将 TCP 和 MAVLink 封装为一个可直接调用的 Python 类，为上层 ROS 节点提供统一的飞控控制接口。

从代码阅读和后续维护角度看，这个文件最值得重点关注的不是初始化过程，而是：

- `handleMessage()` 如何解析并缓存飞控状态
- `setPosition()` 如何把相对位移转换成目标点
- `setGlobalPosition()` 如何发送绝对目标

如果后续要做追踪算法增强、控制逻辑重构、坐标系修正、状态观测扩展，这三个位置几乎一定会成为主要改动点。
