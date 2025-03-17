# GitHub Actions自动构建指南

本指南将帮助您使用GitHub Actions自动构建Windows可执行文件，无需在本地进行打包。

## 步骤1：创建GitHub仓库

1. 登录您的GitHub账号
2. 点击右上角的"+"图标，选择"New repository"
3. 填写仓库名称，例如"xiaohongshu-feishu-tool"
4. 选择"Public"或"Private"（根据您的需求）
5. 点击"Create repository"创建仓库

## 步骤2：上传代码到GitHub仓库

### 方法一：使用Git命令行

1. 在本地创建一个新文件夹，并将所有文件放入其中
2. 打开命令提示符或终端，进入该文件夹
3. 执行以下命令：

```bash
# 初始化Git仓库
git init

# 添加所有文件
git add .

# 提交更改
git commit -m "Initial commit"

# 添加远程仓库
git remote add origin https://github.com/您的用户名/xiaohongshu-feishu-tool.git

# 推送到GitHub
git push -u origin main
```

### 方法二：使用GitHub网页界面上传

1. 在GitHub仓库页面，点击"Add file"按钮，选择"Upload files"
2. 拖拽文件到上传区域，或点击"choose your files"选择文件
3. 添加提交信息，点击"Commit changes"

## 步骤3：确保文件结构正确

您的仓库应该包含以下文件和目录：

```
xiaohongshu-feishu-tool/
├── .github/
│   └── workflows/
│       └── build_exe.yml
├── simple_gui.py
└── README.md
```

## 步骤4：触发GitHub Actions构建

GitHub Actions会在以下情况自动触发构建：

1. 当您推送代码到main分支时
2. 当您创建Pull Request到main分支时
3. 手动触发（在Actions页面点击"Run workflow"按钮）

## 步骤5：下载构建产物

1. 在GitHub仓库页面，点击"Actions"选项卡
2. 找到最新的成功构建（绿色对勾图标）
3. 点击该构建查看详情
4. 在页面底部的"Artifacts"部分，点击"小红书笔记提取工具"下载exe文件

## 步骤6：运行可执行文件

下载的文件是一个zip压缩包，解压后即可获得exe文件，双击运行即可。

## 常见问题

### 构建失败怎么办？

1. 点击失败的构建查看详情
2. 检查日志，找出失败原因
3. 修复问题后重新提交代码

### 如何修改代码？

1. 在本地修改simple_gui.py文件
2. 提交并推送更改到GitHub
3. GitHub Actions会自动构建新的exe文件

### 如何查看构建状态？

在README.md文件中添加构建状态徽章：

```markdown
![Build Status](https://github.com/您的用户名/xiaohongshu-feishu-tool/actions/workflows/build_exe.yml/badge.svg)
```

### 如何设置私有仓库的访问权限？

如果您使用私有仓库，可以在仓库设置中邀请其他用户访问：

1. 在仓库页面，点击"Settings"
2. 点击左侧的"Collaborators"
3. 点击"Add people"添加协作者

## 注意事项

1. GitHub Actions对免费账户有一定的使用限制，但对于个人项目通常足够
2. 构建过程可能需要几分钟时间，请耐心等待
3. 如果长时间不使用，GitHub可能会自动归档您的仓库，需要手动重新激活
