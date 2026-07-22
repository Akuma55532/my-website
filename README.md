# 如何共同维护这个网站

这是一个使用 [Docusaurus](https://docusaurus.io/) 构建的静态文档网站。文档写在 `docs/`，图片、音频等资源放在 `static/`；运行构建后会生成可部署的网站到 `build/`。

## 环境要求

- Git
- [Node.js 22](https://nodejs.org/)
- npm（随 Node.js 安装）

先确认环境：

```bash
git --version
node --version
npm --version
```

## 获取项目并启动

首次参与时，建议先在 GitHub 上 Fork 本仓库，再克隆自己的 Fork：

```bash
git clone git@github.com:<你的 GitHub 用户名>/my-website.git
cd my-website
npm install
npm run start
```

浏览器打开命令行显示的地址（通常是 `http://localhost:3000`）。保存 Markdown、MDX、React 或 CSS 文件后，页面会自动刷新。

如果 Windows PowerShell 提示禁止运行 `npm.ps1`，请将命令中的 `npm` 改为 `npm.cmd`，例如：

```powershell
npm.cmd run start
```

## 文档如何组织

```text
docs/       文档源文件；每个 .md / .mdx 文件对应一个页面
static/     图片、音频等静态资源；网站中用 /文件路径 引用
src/        首页、组件和全局样式
docusaurus.config.js  站点名称、地址、导航、主题等配置，因为目前是测试阶段，所以这些配置不用管
sidebars.js 文档侧栏配置；当前按 docs/ 目录自动生成
```

### 新增或修改文档

1. 在合适的 `docs/` 子目录中新建或编辑 `.md` 文件。
2. 用 Markdown 编写内容；图片放进对应的 `static/` 子目录，并使用相对站点路径引用，例如：

   ```md
   ![树莓派接线图](/产品使用手册/产品通用/飞控物理接口.png)
   ```

3. 运行本地网站检查页面、图片与侧栏是否正常。
4. 新目录需要显示名称或排序时，在目录中添加 `_category_.json`：

   ```json
   {
     "label": "目录名称",
     "position": 1
   }
   ```

请使用清晰、稳定的文件名；已有资源主要使用中文目录和文件名，新文件应与所在目录保持一致。不要编辑 `build/`、`node_modules/` 或 `.docusaurus/`，它们都是生成内容。

具体可以参考我已经写的一些内容。

## 提交前检查

```bash
npm run build
```

```bash
npm run server
```

## 与他人协作

你的改动单独使用一个分支，避免直接提交到 `main`：

如果你准备合并到主分支，在 GitHub 创建 Pull Request，简要说明修改内容和已执行的检查。提交前先 `git status`，不要把无关的本地改动一并提交。
