"""配置管理模块"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class OpenAIConfig(BaseModel):
    """OpenAI配置"""
    api_key: str = Field(..., description="OpenAI API Key")
    base_url: Optional[str] = Field(default=None, description="OpenAI API Base URL")
    model: str = Field(default="gpt-3.5-turbo", description="使用的模型")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="温度参数")
    max_tokens: Optional[int] = Field(default=2000, description="最大token数")
    timeout: int = Field(default=60, description="请求超时时间（秒）")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=1.0, description="重试延迟（秒）")
    
    def update_api_key(self, api_key: str) -> None:
        """更新API Key"""
        if api_key:
            self.api_key = api_key


class ExtractionConfig(BaseModel):
    """知识抽取配置"""
    chunk_size: int = Field(default=2000, description="文档分块大小")
    chunk_overlap: int = Field(default=200, description="分块重叠大小")
    max_chunks_per_request: int = Field(default=5, description="每次请求的最大分块数")
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="最小置信度阈值")
    enable_filtering: bool = Field(default=True, description="是否启用结果过滤")
    language: str = Field(default="zh", description="文档语言")
    domain: Optional[str] = Field(default=None, description="专业领域")


class ReasoningConfig(BaseModel):
    """知识推理配置"""
    max_reasoning_depth: int = Field(default=3, description="最大推理深度")
    max_triples_per_query: int = Field(default=20, description="每次查询最大三元组数")
    enable_fuzzy_matching: bool = Field(default=True, description="是否启用模糊匹配")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="相似度阈值")
    reasoning_model: str = Field(default="gpt-3.5-turbo", description="推理使用的模型")


class StorageConfig(BaseModel):
    """存储配置"""
    default_format: str = Field(default="rdf", description="默认存储格式")
    output_dir: str = Field(default="output", description="输出目录")
    backup_enabled: bool = Field(default=True, description="是否启用备份")
    compression: bool = Field(default=False, description="是否启用压缩")
    
    @validator('default_format')
    def validate_format(cls, v):
        allowed_formats = ['rdf', 'json', 'jsonld', 'csv', 'ttl']
        if v not in allowed_formats:
            raise ValueError(f'不支持的格式: {v}, 支持的格式: {allowed_formats}')
        return v


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    file_path: Optional[str] = Field(default=None, description="日志文件路径")
    max_file_size: int = Field(default=10485760, description="日志文件最大大小（字节）")
    backup_count: int = Field(default=5, description="日志备份数量")
    console_output: bool = Field(default=True, description="是否输出到控制台")


class Config(BaseSettings):
    """主配置类"""
    
    # 基础配置
    project_name: str = Field(default="KQuest", description="项目名称")
    version: str = Field(default="0.1.0", description="版本号")
    debug: bool = Field(default=False, description="调试模式")
    
    # 子配置
    openai: OpenAIConfig = Field(..., description="OpenAI配置")
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig, description="抽取配置")
    reasoning: ReasoningConfig = Field(default_factory=ReasoningConfig, description="推理配置")
    storage: StorageConfig = Field(default_factory=StorageConfig, description="存储配置")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="日志配置")
    
    # 路径配置
    config_dir: str = Field(default="config", description="配置文件目录")
    data_dir: str = Field(default="data", description="数据目录")
    temp_dir: str = Field(default="temp", description="临时目录")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False
        
    def __init__(self, **data):
        super().__init__(**data)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.config_dir,
            self.data_dir,
            self.temp_dir,
            self.storage.output_dir,
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_yaml(cls, config_path: Union[str, Path]) -> "Config":
        """从YAML文件加载配置"""
        import yaml
        
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)
    
    def to_yaml(self, config_path: Union[str, Path]) -> None:
        """保存配置到YAML文件"""
        import yaml
        
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.dict(), f, default_flow_style=False, allow_unicode=True)
    
    def get_openai_client_config(self) -> Dict[str, Any]:
        """获取OpenAI客户端配置"""
        config = {
            "api_key": self.openai.api_key,
            "timeout": self.openai.timeout,
            "max_retries": self.openai.max_retries,
        }
        
        if self.openai.base_url:
            config["base_url"] = self.openai.base_url
            
        return config
    
    def update_from_env(self) -> None:
        """从环境变量更新配置（仅更新API Key，保持模型配置不变）"""
        # 只更新API Key，不更新模型配置以确保始终使用配置文件中的设置
        if api_key := os.getenv("OPENAI_API_KEY"):
            self.openai.api_key = api_key
        
        # 其他环境变量
        if debug := os.getenv("DEBUG"):
            self.debug = debug.lower() in ("true", "1", "yes")
        if log_level := os.getenv("LOG_LEVEL"):
            self.logging.level = log_level.upper()
    
    def validate_config(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        
        # 验证OpenAI配置
        if not self.openai.api_key:
            errors.append("OpenAI API Key不能为空")
        
        # 验证抽取配置
        if self.extraction.chunk_size <= 0:
            errors.append("分块大小必须大于0")
        if self.extraction.chunk_overlap < 0:
            errors.append("分块重叠不能为负数")
        if self.extraction.chunk_overlap >= self.extraction.chunk_size:
            errors.append("分块重叠不能大于等于分块大小")
        
        # 验证推理配置
        if self.reasoning.max_reasoning_depth <= 0:
            errors.append("最大推理深度必须大于0")
        if not 0 <= self.reasoning.similarity_threshold <= 1:
            errors.append("相似度阈值必须在0-1之间")
        
        # 验证存储配置
        if not Path(self.storage.output_dir).exists():
            try:
                Path(self.storage.output_dir).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"无法创建输出目录: {e}")
        
        return errors
    
    def get_effective_config(self) -> Dict[str, Any]:
        """获取有效配置（用于调试）"""
        return {
            "project_name": self.project_name,
            "version": self.version,
            "debug": self.debug,
            "openai": {
                "model": self.openai.model,
                "base_url": self.openai.base_url,
                "temperature": self.openai.temperature,
                "max_tokens": self.openai.max_tokens,
                "timeout": self.openai.timeout,
            },
            "extraction": {
                "chunk_size": self.extraction.chunk_size,
                "chunk_overlap": self.extraction.chunk_overlap,
                "max_chunks_per_request": self.extraction.max_chunks_per_request,
                "min_confidence": self.extraction.min_confidence,
                "language": self.extraction.language,
                "domain": self.extraction.domain,
            },
            "reasoning": {
                "max_reasoning_depth": self.reasoning.max_reasoning_depth,
                "max_triples_per_query": self.reasoning.max_triples_per_query,
                "enable_fuzzy_matching": self.reasoning.enable_fuzzy_matching,
                "similarity_threshold": self.reasoning.similarity_threshold,
            },
            "storage": {
                "default_format": self.storage.default_format,
                "output_dir": self.storage.output_dir,
                "backup_enabled": self.storage.backup_enabled,
            },
            "logging": {
                "level": self.logging.level,
                "console_output": self.logging.console_output,
                "file_path": self.logging.file_path,
            },
        }


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例，始终优先使用配置文件中的设置"""
    global _config
    if _config is None:
        # 强制从项目配置文件加载
        project_config_path = "config/config.yaml"
        
        if Path(project_config_path).exists():
            try:
                _config = Config.from_yaml(project_config_path)
                # 只更新API Key，保持其他配置不变
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    _config.openai.update_api_key(api_key)
                print(f"✓ 配置加载成功: {_config.project_name} v{_config.version}")
            except Exception as e:
                print(f"✗ 配置文件加载失败: {e}")
                raise
        else:
            raise FileNotFoundError(f"项目配置文件不存在: {project_config_path}")
    
    return _config


def set_config(config: Config) -> None:
    """设置全局配置实例"""
    global _config
    _config = config


def load_config(config_path: Union[str, Path]) -> Config:
    """加载配置文件并设置为全局配置"""
    config = Config.from_yaml(config_path)
    config.update_from_env()
    set_config(config)
    return config
