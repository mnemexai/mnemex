from cortexgraph.storage.models import (
    ErrorCode,
    ErrorContext,
    ErrorDetail,
    ErrorResponse,
)


def test_error_response_creation():
    detail = ErrorDetail(
        code=ErrorCode.INVALID_INPUT,
        message="Invalid input provided",
        remediation="Check your input",
    )
    response = ErrorResponse(error=detail)
    assert response.success is False
    assert response.error.code == ErrorCode.INVALID_INPUT


def test_error_context_creation():
    context = ErrorContext(
        file="test.py",
        line=10,
        memory_id="mem-1",
        parameter="id",
        value="invalid",
        details="Something went wrong",
    )
    assert context.file == "test.py"
    assert context.details == "Something went wrong"


def test_error_detail_with_context():
    context = ErrorContext(parameter="id", value="123")
    detail = ErrorDetail(
        code=ErrorCode.MEMORY_NOT_FOUND,
        message="Memory not found",
        remediation="Create it first",
        context=context,
    )
    assert detail.context.parameter == "id"
