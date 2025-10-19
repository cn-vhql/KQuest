# 安全注意事项

## 🔒 敏感信息保护

KQuest项目处理配置文件和API密钥，请务必遵循以下安全最佳实践：

### 配置文件安全
1. **永远不要提交真实的配置文件**到版本控制系统
2. 只提交 `config/config.yaml.example` 模板文件
3. 实际配置文件 `config/config.yaml` 已在 `.gitignore` 中被忽略

### API密钥管理
1. 使用环境变量存储敏感信息：
   ```bash
   export OPENAI_API_KEY="your-actual-api-key"
   ```
2. 或在配置文件中使用占位符，运行时替换
3. 定期轮换API密钥
4. 使用最小权限原则配置API访问权限

### 环境隔离
- 为不同环境（开发、测试、生产）使用不同的配置文件
- 使用 `config.config.dev.yaml`, `config.config.prod.yaml` 等命名方式
- 确保生产环境配置文件不被意外提交

### 数据保护
1. **输出目录** (`output/`) 包含抽取的知识图谱，可能包含敏感信息
2. **日志文件** 可能记录API调用和数据处理详情
3. **临时文件** 可能包含未处理的原始数据

### 推荐的安全实践
```bash
# 检查是否有敏感文件被意外跟踪
git ls-files | grep -E "(config\.yaml|\.env|secret|key|password|token)"

# 检查提交历史中是否包含敏感信息
git log --all --full-history -- **/config.yaml
git log --all --full-history -- **/.env*

# 使用 git-secrets 工具防止敏感信息提交
git secrets --register-aws
git secrets --install
```

### 生产环境部署
1. 使用环境变量或密钥管理服务
2. 启用日志加密和访问控制
3. 定期审计访问日志和API使用情况
4. 实施网络隔离和防火墙规则

### 事故响应
如果发现敏感信息泄露：
1. 立即撤销/轮换相关的API密钥
2. 从Git历史中移除敏感信息
3. 检查访问日志确认影响范围
4. 通知相关团队和利益相关者

## 🛡️ 项目特定的安全考虑

### 大模型API安全
- 限制API调用频率和配额
- 监控异常使用模式
- 实施请求签名验证（如果API支持）

### 知识图谱数据
- 评估抽取数据的敏感性级别
- 对敏感实体进行脱敏处理
- 实施访问控制和权限管理

### 文件系统权限
```bash
# 设置适当的文件权限
chmod 600 config/config.yaml
chmod 700 output/
chmod 755 src/kquest/
```

## 📞 报告安全问题

如果发现安全漏洞，请：
1. 不要公开披露
2. 通过私有渠道报告给项目维护者
3. 提供详细的重现步骤
4. 等待修复后再公开披露

---

**记住：安全是每个人的责任！** 🚀
