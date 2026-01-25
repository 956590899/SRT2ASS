技术预览 ！！！！

普通卡拉OK效果展示

![56f745550923dd5479c317739709b3de9d82485a](https://github.com/user-attachments/assets/e34a81cd-404e-4e21-8501-430fb30e3953)

！！！提词器效果展示

![1c2f35dab6fd5266b9858c0fed18972bd5073660](https://github.com/user-attachments/assets/22aa1ab4-3e74-488b-bab2-546b243a73a2)

！！！真实卡拉OK效果展示

![a08959fab2fb4316a980ca6166a4462308f7d370](https://github.com/user-attachments/assets/d02929b5-c5f2-4f47-aaf7-780b3b110096)

Z.py为主程序


效果可通过修改Z.py REAL_KARAOKE_EFFECT = 0 # 真实卡拉OK效果设置：0=默认效果，1=真实卡拉OK式样，2=提词器式样 段转换效果 建议默认效果 （因为自动打轴准确率只能保证80%（歌词语速均匀准确率更高）方便修改）


当你的卡拉ok准确率确认可用后 可通过 .Z1卡拉OK式样-5.1.bat 转换式样或转换音频为5.1（默认未启用） 打开SRT2ASS\SRT\Z1.py STEREO_TO_5_1 = 0 # 0或1（开关5.1音频转换） SUBTITLE_MODE = 1 # 0、1或2 字幕效果转换 （可切换以上效果）


A 字幕校对转换
B 卡拉OK转换逻辑  
C 打包子程序 
K 真实卡拉OK转换逻辑 
T 提词器卡拉OK 转换逻辑
Z 主程序 SRT转ASS 一键处理字幕打包程序 
Z1 卡拉OK式样-5.1 用于字幕效果切换 或者加入5.1音频效果支持
