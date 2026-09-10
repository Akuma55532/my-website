---
sidebar_position: 2
---

# ROS 工程部署

本节以 **Ubuntu 20.04（64 位）+ ROS Noetic** 为例，完成 FanciSwarm® 基础款无人机所需的 Mcontroller ROS 工程环境配置、工程导入和通信节点参数说明。

## 部署前准备

开始前请确认：

- 电脑已安装 Ubuntu 20.04（64 位）；
- 电脑可以正常访问 GitHub 或 Gitee；
- 系统已安装 Git；
- 已了解基本的终端操作，例如复制命令、进入目录和查看命令输出；
- 如需使用 UWB 定位，已阅读上一节 [环境部署](./环境部署.md)。

:::info[本节完成标准]

完成本节后，`~/ros-ws/src` 中应包含 `fcu_core` 工程，并且已经确认通信节点参数与基础款无人机的实际连接方式一致。

:::

## 一、配置电脑环境

### 1. 安装 ROS Noetic

如果电脑尚未安装 ROS，请先按照通用教程完成 [ROS Noetic 安装](../../../通用教程/ROS/安装ROS.md)。安装结束后打开终端，执行：

```bash
rosversion -d
```

终端输出 `noetic`，说明当前 ROS 发行版正确。

### 2. 打开终端

在 Ubuntu 桌面空白处单击鼠标右键，选择 **Open in Terminal**。

![在 Ubuntu 桌面右键菜单中打开终端](/产品使用手册/使用手册/基础款/terminal.png)

后续命令均在终端中执行。输入需要 `sudo` 权限的命令时，系统会要求输入 Ubuntu 用户密码；输入过程中终端不会显示字符，这是正常现象，输入完成后按回车键即可。

### 3. 安装 ROS 串口功能包

先更新软件包索引：

```bash
sudo apt-get update
```

然后安装 ROS Noetic 的串口功能包：

```bash
sudo apt-get install ros-noetic-serial
```

![在终端中安装 ros-noetic-serial 功能包](/产品使用手册/使用手册/基础款/sudo-uart.png)

安装完成后，终端会显示已安装的版本信息；如果系统提示该软件包已经是最新版本，也表示安装正常。

![ros-noetic-serial 功能包安装成功](/产品使用手册/使用手册/基础款/sudo-uart2.png)

可使用下面的命令再次确认软件包状态：

```bash
dpkg -s ros-noetic-serial
```

输出中出现 `Status: install ok installed`，表示安装成功。

### 4. 安装 Eigen 库

Eigen 是一个开源 C++ 线性代数库，提供矩阵、向量、数值分析等相关功能。执行：

```bash
sudo apt-get install libeigen3-dev
```

![在终端中安装 libeigen3-dev](/产品使用手册/使用手册/基础款/eigen1.png)

安装完成后，终端会显示 Eigen 的版本信息；如果提示已经是最新版本，也表示安装正常。

![Eigen 库安装成功](/产品使用手册/使用手册/基础款/eigen2.png)

可使用下面的命令确认 Eigen 已安装：

```bash
dpkg -s libeigen3-dev
```

## 二、导入 ROS 工程

### 1. 了解 Mcontroller ROS 工程

FanciSwarm® 使用的 Mcontroller ROS 工程仓库名为 `fcu_core`。工程运行在远程电脑上，电脑与无人机进行数据交互：无人机向电脑发送状态数据，电脑向无人机发送定位数据或控制指令。

`fcu_core` 采用分布式节点设计，每一架与 ROS 工程通信的无人机对应一个唯一通信节点：

| 无人机标签 ID | ROS 通信节点 | 对应源文件 |
| ---: | --- | --- |
| 1 | 001 | `fcu_bridge_001.cpp` |
| 2 | 002 | `fcu_bridge_002.cpp` |
| 3 | 003 | `fcu_bridge_003.cpp` |
| … | … | 按相同编号规则创建 |

工程中已经创建了 6 个通信节点。单机轨迹飞行只需要使用通信节点 001；多机集群飞行需要为参与飞行的每架无人机使用对应节点。

工程仓库：

- [GitHub：fancinnov/fcu_core](https://github.com/fancinnov/fcu_core)
- [Gitee：fancinnov/fcu_core](https://gitee.com/fancinnov/fcu_core)

### 2. 创建工作空间

工作空间可以理解为 ROS 工程目录。本教程统一在当前用户的主目录下创建 `ros-ws`：

```bash
cd ~
mkdir ros-ws
```

创建完成后，可以在文件管理器中看到 `ros-ws` 文件夹。官网截图将文件夹放在桌面，实际使用时以终端中创建的路径为准。

![创建 ros-ws 工作空间文件夹](/产品使用手册/使用手册/基础款/ros-ws.png)

:::note[如果 ros-ws 已经存在]

不要重复创建或删除原文件夹。先确认其中没有同名工程，再继续执行后续步骤。

:::

### 3. 创建 src 文件夹

进入工作空间并创建用于存放工程源码的 `src` 文件夹：

```bash
cd ~/ros-ws
mkdir src
```

操作完成后，`ros-ws` 下应出现 `src` 子文件夹。

![ros-ws 工作空间中的 src 文件夹](/产品使用手册/使用手册/基础款/src.png)

进入 `src` 文件夹后，可以在空白处单击鼠标右键并选择 **Open in Terminal**；也可以直接使用下面的命令进入该目录：

```bash
cd ~/ros-ws/src
```

![在 src 文件夹中打开终端](/产品使用手册/使用手册/基础款/src2.png)

### 4. 克隆 fcu_core 工程

国内网络环境建议使用 Gitee：

```bash
cd ~/ros-ws/src
git clone https://gitee.com/fancinnov/fcu_core.git
```

如果使用 GitHub，则执行：

```bash
cd ~/ros-ws/src
git clone https://github.com/fancinnov/fcu_core.git
```

![使用 Git 克隆 fcu_core 工程](/产品使用手册/使用手册/基础款/clone.png)

克隆完成后，`~/ros-ws/src` 下会出现 `fcu_core` 文件夹。

![src 文件夹中的 fcu_core 工程](/产品使用手册/使用手册/基础款/clone2.png)

:::warning[不要重复克隆]

如果 `src` 中已经存在 `fcu_core` 文件夹，不要再次执行 `git clone`。需要获取仓库更新时，应先确认本地代码没有未保存的改动，再在工程目录中使用 Git 更新。

:::

## 三、配置通信节点参数

### 1. 打开通信节点文件

单机轨迹飞行只需要检查通信节点 001。打开以下文件：

```text
~/ros-ws/src/fcu_core/src/fcu_bridge_001.cpp
```

文件顶部包含通信方式、无人机地址和定位方式等参数。

![fcu_bridge_001.cpp 顶部的通信节点参数](/产品使用手册/使用手册/基础款/fcu001.png)

### 2. 参数说明

| 参数 | 工程示例值 | 说明 |
| --- | --- | --- |
| `BUF_SIZE` | `32768` | 通信缓存区大小，即 32 KB。快速使用阶段保持默认值。 |
| `BAUDRATE` | `460800` | USB 虚拟串口波特率，仅串口通信时使用。 |
| `DRONE_PORT` | `333` | 网络通信端口，默认不需要修改。 |
| `DRONE_IP` | `192.168.4.1` | 无人机网络通信 IP。电脑直连单机默认 Mlink Wi-Fi 时通常保持默认值；如果已配置组网模块，应填写对应无人机的实际 IP。 |
| `USB_PORT` | `/dev/ttyACM0` | USB 虚拟串口设备路径，仅串口通信时使用。 |
| `mav_chan` | `MAVLINK_COMM_1` | `MAVLINK_COMM_0` 表示 USB 虚拟串口通信，`MAVLINK_COMM_1` 表示网口通信；基础款默认使用网口通信。 |
| `offboard` | `false` | 是否使用机载电脑。基础款无人机没有机载电脑，保持 `false`。 |
| `use_uwb` | `true` | 是否使用 UWB 基站。轨迹飞行和集群飞行需要 UWB 定位，保持 `true`。 |
| `set_goal` | `false` | 与轨迹规划目标点的数据来源有关。当前工程示例值为 `false`，快速使用阶段保持工程默认值。 |
| `simple_target` | `true` | 仅机载电脑方案需要配置；表示目标点只包含位置，不包含速度和加速度。基础款快速使用阶段无需修改。 |

:::danger[请核对通信参数]

如果使用网口通信，`DRONE_IP` 必须与实际连接的无人机 IP 一致。集群飞行时，每个通信节点应对应唯一无人机，节点文件编号、无人机标签 ID 和无人机 IP 不得混淆。

:::

## 四、部署检查

继续后续飞行步骤前，请逐项确认：

- `rosversion -d` 输出 `noetic`；
- `ros-noetic-serial` 和 `libeigen3-dev` 均已安装；
- `~/ros-ws/src/fcu_core` 目录存在；
- 通信节点文件中的 `DRONE_IP` 与实际无人机一致；
- 基础款使用网口通信时，`mav_chan` 为 `MAVLINK_COMM_1`；
- 基础款没有机载电脑，`offboard` 保持 `false`；
- 使用 UWB 轨迹飞行或集群飞行时，`use_uwb` 保持 `true`。

:::tip[常见问题]

- 提示找不到 `serial/serial.h`：重新确认 `ros-noetic-serial` 是否安装成功；
- 提示找不到 Eigen：重新确认 `libeigen3-dev` 是否安装成功；
- `git clone` 速度慢或失败：在 GitHub 与 Gitee 地址之间切换后重试。

:::
