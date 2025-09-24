from app.services.parser_service import ParserService


def test_parser_invoice_extracts_amount():
    parser = ParserService()
    text = "Invoice Total: $123.45 on 2024-01-31 Vendor: ACME Corp"
    result = parser.parse("invoice", text)
    assert result.fields.get("total_amount") == 123.45

