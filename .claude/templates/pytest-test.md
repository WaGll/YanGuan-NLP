# Template: 新建测试

## 使用说明

复制此模板创建新的测试文件。替换 `{{placeholders}}`。

## 文件位置
- 单元测试: `backend/tests/test_{{module_name}}.py`
- API 集成测试: `backend/tests/test_api/test_{{module_name}}.py`

## 单元测试模板

```python
"""测试 {{被测模块中文名}}。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class Test{{ClassName}}:
    """{{被测类名}} 的单元测试。"""

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------
    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话。"""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """创建被测 Service 实例。"""
        from app.services.{{module_name}} import {{ServiceName}}Service
        # 如果需要 mock NLPResources 或其他依赖：
        # with patch("app.services.{{module_name}}.Dependency") as mock_dep:
        #     mock_dep.return_value = ...
        return {{ServiceName}}Service(mock_db)

    # ------------------------------------------------------------------
    # 测试：正常流程
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_{{method_name}}_normal(self, service, mock_db):
        """测试正常输入的处理结果。"""
        # Arrange
        mock_db.execute.return_value.scalars.return_value.all.return_value = [
            MagicMock(id=1, field="value"),
        ]

        # Act
        result = await service.get_results()

        # Assert
        assert len(result) > 0
        assert result[0]["id"] == 1

    # ------------------------------------------------------------------
    # 测试：空数据
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_{{method_name}}_empty(self, service, mock_db):
        """测试空数据库的处理结果。"""
        # Arrange
        mock_db.execute.return_value.scalars.return_value.all.return_value = []

        # Act
        result = await service.get_results()

        # Assert
        assert result == []

    # ------------------------------------------------------------------
    # 测试：异常处理
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_{{method_name}}_error(self, service, mock_db):
        """测试数据库错误时的异常处理。"""
        # Arrange
        mock_db.execute.side_effect = Exception("数据库连接失败")

        # Act & Assert
        with pytest.raises(Exception, match="数据库连接失败"):
            await service.get_results()

    # ------------------------------------------------------------------
    # 测试：边界条件
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_{{method_name}}_edge_cases(self, service):
        """测试边界条件。"""
        # 空输入
        # None 输入
        # 极大值/极小值
        # 特殊字符
        pass
```

## API 集成测试模板

```python
"""测试 {{模块中文名}} API 端点。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_{{endpoint}}_normal(test_client: AsyncClient):
    """测试正常响应（200）。"""
    response = await test_client.get("/api/{{endpoint_path}}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"] is not None


@pytest.mark.asyncio
async def test_{{endpoint}}_empty(test_client: AsyncClient):
    """测试空数据库响应。"""
    response = await test_client.get("/api/{{endpoint_path}}")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_{{endpoint}}_pagination(test_client: AsyncClient):
    """测试分页参数。"""
    # 正常分页
    response = await test_client.get("/api/{{endpoint_path}}?page=1&page_size=10")
    assert response.status_code == 200

    # 超出范围 page_size
    response = await test_client.get("/api/{{endpoint_path}}?page_size=200")
    assert response.status_code == 422  # 超出 max=100

    # 负数 page
    response = await test_client.get("/api/{{endpoint_path}}?page=-1")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_{{endpoint}}_detail_not_found(test_client: AsyncClient):
    """测试不存在的资源（404）。"""
    response = await test_client.get("/api/{{endpoint_path}}/99999")
    assert response.status_code == 404
```

## 清单

添加新测试时需要检查：
- [ ] 测试文件以 `test_` 开头
- [ ] 测试函数以 `test_` 开头
- [ ] 测试类以 `Test` 开头
- [ ] 每个测试函数有文档字符串描述场景
- [ ] 使用 `@pytest.mark.asyncio`（如未设置 `asyncio_mode = "auto"`）
- [ ] API 测试使用 `test_client` fixture（来自 `conftest.py`）
- [ ] 覆盖正常、空数据、参数错误、资源不存在四种场景
- [ ] 测试之间独立（不依赖其他测试的副作用）
- [ ] 运行 `pytest tests/test_{{name}}.py -v` 确认通过
