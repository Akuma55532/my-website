---
sidebar_position: 3
---

# `fcu_bridge.py`

## 1. 文件定位

`fcu_bridge.py` 是整个工程中的 ROS 桥接层节点。

它的核心职责是把上层 ROS 世界和底层飞控通信模块 `droneClass.py` 连接起来。

更具体地说，它负责三件事：

- 从 ROS 参数读取飞控连接配置
- 订阅手动控制和追踪控制相关 topic，并转发给飞控
- 把飞控状态重新封装成 ROS topic，供 RViz、panel 和其他节点使用

如果说 `droneClass.py` 是“飞控通信驱动层”，那么 `fcu_bridge.py` 就是“ROS 适配层”。

---

## 2. 在系统中的位置

从整个工程的数据流来看，`fcu_bridge.py` 位于中间位置：

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

它本身不做视觉识别，也不直接处理 MAVLink 字节流，而是负责：

- 接 ROS 消息
- 调 `droneClass` 的接口
- 再把飞控状态转成 ROS 消息发出去

所以，这个文件最值得关注的部分不是启动样板，而是：

- 连接管理逻辑
- 遥测发布逻辑
- 各类控制命令的桥接逻辑
- 追踪控制的启停与门控逻辑

---

## 3. 初始化阶段简述

初始化入口位于 FcuBridgeNode.__init__()。

这一部分主要做了这些事情：

- 读取 ROS 参数，比如 `host`、`port`、`heartbeat_rate`、`telemetry_rate`
- 创建若干 ROS Publisher 和 Subscriber
- 初始化桥接状态量，如 `tracking_enabled`、`tracking_valid`
- 启动两个 ROS 定时器：
  - 心跳定时器
  - 遥测发布定时器

这部分一般不属于二次开发的高频改动区，除非：

- 通信地址和连接方式发生变化
- 需要新增或删减 topic
- 需要修改心跳频率或遥测频率

---

## 4. 核心数据流

`fcu_bridge.py` 的核心数据流可以分成两条：

### 4.1 控制下行链

```text
RViz panel / 感知节点发布 ROS 控制消息
                ↓
      fcu_bridge 订阅并解析消息
                ↓
      调用 droneClass 对应控制接口
                ↓
          droneClass 发送 MAVLink
                ↓
                 FCU
```

### 4.2 状态上行链

```text
FCU 状态 → droneClass 缓存位置/姿态/电池
                    ↓
        fcu_bridge 定时读取缓存
                    ↓
      发布 position / attitude / battery 等 ROS topic
                    ↓
          RViz / Panel / 其他节点
```

所以从技术文档角度看，这个文件真正重要的是“桥接规则”，而不是底层通信细节。

---

## 5. 连接管理逻辑

连接管理的核心在以下几个函数：

- spin()
- _ensure_connection()
- _disconnect()

### 5.1 `spin()` 的作用

`spin()` 是节点主循环：

```python
while not rospy.is_shutdown():
    self._ensure_connection()
    rate.sleep()
```

它并不直接处理控制消息，而是周期性检查与飞控的连接是否存在。  
真正的控制处理发生在 subscriber 回调和 timer 回调里。

### 5.2 `_ensure_connection()` 的作用

这个函数负责在“当前未连接”时尝试建立连接。

关键逻辑：

```python
if self.drone is not None and self.drone.connected:
    return
```

说明如果连接还在，就不重复重连。

然后又用：

```python
if (now - self.last_connect_attempt).to_sec() < self.reconnect_interval:
    return
```

限制重连频率，避免在掉线时疯狂尝试连接。

真正连接时，会创建：

```python
self.drone = droneClass(self.host, self.port)
self.listener_thread = threading.Thread(target=self.drone.droneListen, daemon=True)
self.listener_thread.start()
```

也就是说：

- `fcu_bridge` 自己不解析 MAVLink
- 它只是实例化 `droneClass`
- 再启动 `droneListen()` 线程持续接收飞控状态

### 5.3 二次开发最常改的内容

连接管理部分后续最常见的改动有：

- 把 TCP 换成其他通信方式
- 调整重连频率和失败处理方式
- 增加更细的连接状态上报
- 给连接过程加入初始化握手或模式检查

如果以后你需要做更稳健的工程部署，这一段通常会被增强。

---

## 6. 遥测发布逻辑

遥测发布核心在：

- _telemetry_timer()

这个函数由 ROS 定时器周期调用，用于把 `droneClass` 缓存的飞控状态发布出去。

### 6.1 发布的位置消息

关键代码：

```python
position_msg = PointStamped()
position_msg.point.x = self.drone.position_x
position_msg.point.y = self.drone.position_y
position_msg.point.z = self.drone.position_z
self.position_pub.publish(position_msg)
```

这意味着 `fcu_bridge` 并不重新计算位置，而是直接转发 `droneClass` 中缓存的值。

### 6.2 发布的姿态消息

关键代码：

```python
attitude_msg.vector.x = self.drone.att_roll
attitude_msg.vector.y = self.drone.att_pitch
attitude_msg.vector.z = self.drone.att_yaw
```

这里使用的是 `Vector3Stamped` 来表示 roll、pitch、yaw。

### 6.3 发布的电池消息

关键代码：

```python
self.battery_voltage_pub.publish(Float32(data=self.drone.battery_voltage))
self.battery_current_pub.publish(Float32(data=self.drone.battery_current))
```

### 6.4 这一段为什么重要

如果后续你需要：

- 在 RViz 里显示更多飞控状态
- 给 UI 增加模式、电量、速度、飞行状态显示
- 给其他节点提供更多控制反馈

通常都会从 `_telemetry_timer()` 扩展。

### 6.5 二次开发常见改法

- 新增 publisher，发布速度、模式、GPS 等信息
- 改消息类型，比如把姿态改成 `Quaternion` 或自定义消息
- 给异常值增加过滤
- 增加 `connected`、`tracking_enabled` 之外的状态 topic

---

## 7. 手动控制桥接逻辑

这部分是 `fcu_bridge.py` 最值得详细说明的部分之一，因为 RViz panel 的手动按钮几乎都走这里。

相关函数包括：

- _handle_command()
- _handle_set_position()
- _handle_set_global_position()
- _handle_set_yaw()

### 7.1 字符串命令桥接 `_handle_command()`

`/fcu_bridge/command` topic 用字符串表示高层命令，例如：

- `arm`
- `disarm`
- `takeoff`
- `land`

这些命令先通过字典映射：

```python
self.command_handlers = {
    "arm": lambda: self.drone.setArm(),
    "disarm": lambda: self.drone.setDisarm(),
    "takeoff": lambda: self.drone.setTakeoff(),
    "land": lambda: self.drone.setLand(),
}
```

然后在 `_handle_command()` 中根据字符串选择对应函数执行。

这是一种很清晰的命令分发方式，二次开发时如果你要新增高级命令，比如：

- `hover`
- `return_home`
- `emergency_stop`

通常就是在这里扩展。

### 7.2 相对位置桥接 `_handle_set_position()`

关键代码：

```python
lambda: self.drone.setPosition(msg.x, msg.y, msg.z, self._get_relative_target_yaw())
```

这说明：

- 来自 ROS 的 `Vector3` 被解释成相对位移
- `x/y/z` 直接作为相对移动量传给 `droneClass.setPosition()`
- yaw 并不是来自这条消息，而是由 `target_yaw` 和当前姿态差值算出来

这也是后续二次开发常改的地方，因为你可能会希望：

- 手动平移时完全不带 yaw
- 手动平移和 yaw 控制互相独立
- 改成速度控制而不是位移控制

### 7.3 绝对位置桥接 `_handle_set_global_position()`

关键代码：

```python
lambda: self.drone.setGlobalPosition(msg.x, msg.y, msg.z, self.target_yaw)
```

这里说明：

- 绝对位置控制走 `setGlobalPosition()`
- yaw 仍然来自内部保存的 `target_yaw`

### 7.4 偏航控制 `_handle_set_yaw()`

这一段很关键，因为它体现了当前工程里 yaw 的定义方式。

关键代码：

```python
self.target_yaw = self.drone.att_yaw + yaw_offset
self.drone.setGlobalPosition(
    self.drone.position_x,
    self.drone.position_y,
    self.drone.position_z,
    self.target_yaw,
)
```

也就是说：

- panel 发来的 `set_yaw` 不是绝对朝向
- 而是“相对当前朝向的偏航增量”
- `fcu_bridge` 先把它转换成绝对 `target_yaw`
- 再发送一次“当前位置不变，仅修改 yaw”的全局目标

### 7.5 这一段的二次开发价值

手动控制桥接部分是二次开发中非常高频的改动区域，因为：

- UI 交互习惯会变
- 控制语义会变
- 你可能会从“位置控制”改成“速度控制”
- 也可能会把 yaw 从相对量改成绝对量

所以如果后续要调手感、调交互、调控制模式，这部分通常是第一批会改的代码。

---

## 8. 追踪控制桥接逻辑

这部分是 `fcu_bridge.py` 的另一个核心价值所在。  
YOLO 和 ArUco 节点虽然负责生成追踪控制量，但真正把追踪控制量送到飞控的，是这里。

相关函数：

- _handle_tracking_enabled()
- _handle_tracking_valid()
- _handle_tracking_cmd()

### 8.1 追踪使能状态

```python
self.tracking_enabled = msg.data
self.tracking_enabled_state_pub.publish(Bool(data=self.tracking_enabled))
```

这里做了两件事：

- 更新内部的追踪开关状态
- 把状态重新发布出去，供 panel 显示

### 8.2 追踪目标有效状态

```python
self.tracking_valid = msg.data
```

这里不做控制，只负责记录“当前检测节点是否认为目标有效”。

### 8.3 追踪控制命令门控

真正重要的是 `_handle_tracking_cmd()`：

```python
if not self.tracking_enabled or not self.tracking_valid:
    return
```

这行代码定义了追踪控制能否真正下发的门控条件：

- 用户必须打开追踪
- 检测节点必须确认当前有有效目标

只有同时满足这两个条件，追踪控制命令才会被送到飞控。

### 8.4 追踪命令实际发送

关键代码：

```python
lambda: self.drone.setPosition(msg.linear.x, msg.linear.y, msg.linear.z, msg.angular.z)
```

这说明当前工程的追踪控制语义是：

- `Twist.linear.x/y/z` 被当成相对位移量
- `Twist.angular.z` 被当成 yaw 相对增量

这个设计简单直观，但它也意味着：

- `Twist` 在这里不是速度控制含义
- 而是“借用了 Twist 消息结构来承载位置增量”

这是二次开发时必须明确的一点。

### 8.5 这一段为什么最值得改

如果以后你要增强追踪功能，这部分通常是最容易被改动的桥接层位置。常见改法有：

- 把 `Twist` 语义从位移增量改成速度命令
- 加入追踪命令限幅
- 引入优先级管理，避免手动控制与追踪控制冲突
- 给追踪命令加入超时失效机制
- 区分前视和下视时不同的控制解释方式

---

## 9. 统一执行入口 `_run_command()`

函数位置：

- _run_command()

这个函数把所有具体控制执行统一包了一层。

逻辑很简单：

1. 如果飞控未连接，直接拒绝执行
2. 如果已连接，就调用传入的回调
3. 如果执行异常，则打印 warning 并主动断开连接

关键代码：

```python
if self.drone is None or not self.drone.connected:
    rospy.logwarn("Ignoring %s command because FCU is disconnected", name)
    return
```

以及：

```python
except Exception as exc:
    rospy.logwarn("%s command failed: %s", name, exc)
    self._disconnect()
```

### 9.1 这一层的意义

它把“连接检查”和“异常处理”从各个回调中抽离出来，避免重复代码。

### 9.2 二次开发常见改动

这一层后续常被扩展为：

- 增加命令节流
- 增加命令执行日志
- 增加命令队列
- 增加失败重试
- 对不同类型命令采用不同错误策略

如果以后控制逻辑变复杂，这一层很可能成为统一调度入口。

---

## 10. yaw 与位姿辅助逻辑

这部分虽然代码不多，但对控制行为有直接影响。

相关函数：

- _has_valid_pose()
- _get_relative_target_yaw()

### 10.1 `_has_valid_pose()`

当前实现是：

```python
return (
    self.drone.position_x != 0
    and self.drone.position_y != 0
    and self.drone.position_z != 0
)
```

它的作用是判断飞控位姿是否“初始化完成”，主要用于 `_handle_set_yaw()`。

但这个判断方式存在明显问题：  
只要位置恰好在原点附近，函数就会返回 `False`，即使位姿其实是有效的。

这是后续二次开发非常值得优先修正的一处。

### 10.2 `_get_relative_target_yaw()`

当前实现是：

```python
return self.target_yaw - self.drone.att_yaw
```

它把内部保存的绝对 `target_yaw` 转回“相对当前朝向的 yaw 增量”，供 `setPosition()` 使用。

这说明当前系统中同时存在两种 yaw 语义：

- `target_yaw`：绝对目标朝向
- `setPosition()` 输入的 yaw：相对增量

如果后续要统一控制语义，这里通常也会跟着改。

---

## 11. 总结

`fcu_bridge.py` 是本工程里最核心的桥接节点，它把 ROS topic 世界和飞控控制世界连接了起来。  
它本身不实现视觉算法，也不直接做 MAVLink 字节解析，而是负责：

- 管理飞控连接
- 转发手动和自动控制命令
- 发布位置、姿态、电池等遥测信息
- 对追踪控制进行开关与有效性门控

从代码阅读和后续维护的角度看，这个文件最值得重点关注的不是初始化过程，而是：

- `_telemetry_timer()` 如何发布飞控状态
- `_handle_set_position()` / `_handle_set_yaw()` 如何解释手动控制
- `_handle_tracking_cmd()` 如何解释和下发追踪控制
- `_run_command()` 如何统一执行和处理错误

如果后续要做追踪增强、控制优先级仲裁、状态扩展、通信稳定性优化，`fcu_bridge.py` 会是最主要的修改入口之一。
