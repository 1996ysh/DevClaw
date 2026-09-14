## todo sandbox is so abstract and hard
"""
整体模式：**容器提前启动常驻后台 sleep infinity，不销毁；
后续全部靠 `docker exec / docker cp` 在已经运行的容器内部执行代码、上传下载文件**
不是每次执行代码新建销毁容器；容器生命周期交给外部`docker_manager.py`管理，docker_sandbox只管操作已经存在的容器。
"""
"""
BaseSandbox（抽象基类）
    ↓ 子类实现全部4个契约
DockerSandbox
 ├ id 属性 → 返回容器id
 ├ execute() → docker exec 在容器执行shell命令
 ├ upload_files() → docker cp：宿主机临时文件拷贝进容器
 └ download_files() → docker cp：容器文件拷贝到宿主机临时文件读取字节
 本类写的全部是**同步函数**，
 框架底层会用`asyncio.to_thread()`包装，
 变成异步`aexecute()`，
 避免阻塞 FastAPI 主事件循环。
"""