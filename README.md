**v1.7版本**
升级：

1.去除多语言

2.去除频道选择，改为频率，模拟40m波段

3.弃用自己写的简单后端，改用开源版emqx

4.动画增加10个侧信道，共十一个信道，中间蓝色部分为主信道

5.弃用WPM微调，手动填写改为滑动条设置

6.改进解码器，增加误差范围，手感更加柔和

7.增加多端互通功能，同时发布的还有安卓版


修复：

1.连接器改键，模拟鼠标不正确

注意：

1.此版本需要先设置呼号才能使用，如果没有呼号可以自己填写一个字母+数字的虚拟呼号

![主页截图&home page screenshout](https://github.com/TateLuo/MorseLink/blob/main/screen_shot/1.7.0.png)


-------------------------------------------------------------

**v1.6版本**
优化升级：

1.优化MorseLink Connector电键连接器的界面，更加易于使用。增加按键Ctrl可以用于MorseRunner连接电键发报。

2.增加语言英语，可自动适配系统语言或者手动切换。

3.软件内在线下载更新改为弹窗至浏览器下载（服务器带宽较低下载速度慢，第三方下载服务会有更快的下载速度）

4.添加软件安装程序，不会再因为程序升级产生冲突

修复BUG:

1.或许修复了一些已知Bug

2.如果发现有新的BUG，麻烦联系作者BI4MOL，会在下个版本中进行修复。

![主页截图&home page screenshout](https://github.com/TateLuo/MorseLink/blob/main/screen_shot/1.6.0.png)

-------------------------------------------------------------

**v1.5版本**
优化升级：

1.优化界面，适配了高分辨率系统，文字更清晰

2.新增发报训练功能

3.新增发报记录图形化回放

4.优化收报的逻辑，优化僵硬的声音，可听出手法。


修复BUG:

1.重写禁止发报逻辑(貌似不用重写)

2.呼号不能设置，发报按键为松开时切换软件声音不停止

3.听力课程停止播放后，进度条应该清零

4.听力课程，点击标题可以查看一次本课核心内容

5.弹出不存在对象call of sender

![主页截图&home page screenshout](https://github.com/TateLuo/MorseLink/blob/main/screen_shot/1.5.0.png)

-------------------------------------------------------------
**V1.4版本**

升级：

1.字体大小自适应【改成自己设置字体】

2.增加在线更新功能

修复的bug:

1.连接音频外设时，播放音频会报错[努力修复中]

2.听力音频无法关闭，即使退出软件仍然播放[已修复]

3.设置按键时，无法设置空格键[已修复]

4.初始化数据库是，先检测是否有对应的表[已修复]

![主页截图&home page screenshout](https://github.com/TateLuo/MorseLink/blob/main/screen_shot/1.4.0.png)

-------------------------------------------------------------
**V1.3版本**

新增功能：

1.听力练习功能

2.一个通信指示灯

3.电键连接器界面新增一个刷新窗口按钮

4.优化了一部分UI界面，增加了图标

5.清理屏幕按钮下移

修复bug:

1.自动键模式按钮按下切换到其他界面时，仍然是按下状态

2.电键连接器写入按键修复无法写入空格键的问题

3.修复动画界面无法随窗口自适应的问题\

![主页截图&home page screenshout](https://github.com/TateLuo/MorseLink/blob/main/screen_shot/1.3.0.png)

----------------------------------------------------------
**V1.2版本：**
1.可手动调整字母间隔，单词间隔(手键，自动键)

2.增加根据键速自动计算时间功能

3.优化自动键模式下音频不跟手的问题，仍未达到最优手感

4.在线更新功能

5.收发报动画流

6.蜂鸣器音频可调

7.增加电键连接器改键功能


修复的问题：

1.连接未断开时不可选择其他频道【已修改】

2.有连接状态更新时不禁止发射【已修复】

3.客户端占用指定端口（或者给一个指定端口范围）【只能指定一个端口，还是不指定了，有电脑分配】

4.在部分电脑上会有音频混响问题，打不开。增加音频播放异常捕捉，不至于部分设备打不开程序，但是可能出现声音播放不了的情况。

![主页截图&home page screenshout](https://github.com/TateLuo/MorseLink/blob/main/screen_shot/1.2.0.png)


--------------------------------------------------------------------------

**V1.1版本**

更新如下：

更名为：MORSELINK

1.全新的主界面UI设计

2.将点击空白处发报改为，点击固定区域发报。

3.增加键盘发报功能

4.增加自动键功能：单点，长按（间隔为点的3倍）

5.取消当前服务器人数显示文本，将所有频道在线人数状态可视化，更加便于操作。

6.设置页，增加自动键开关、电码与翻译显示开关、收发报蜂鸣音开关

7.清理界面转移至菜单栏

8.电码翻译，增加常用符号

9.增加菜单栏帮助选项,帮助选项-（莫斯电码表、常用通联用语）

10.增加自动通联记录功能

11.增加设置自己呼号与通联时显示对方呼号功能

![主页截图&home page screenshout](https://github.com/TateLuo/MorseLink/blob/main/screen_shot/1.1.0.png)
