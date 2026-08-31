from dataclasses import dataclass, field


@dataclass
class ColumnMetadata:
    description: str = None
    is_sensitive: bool = False
    show_samples: bool = True
    unit: str | None = None

@dataclass
class TableMetadata:
    table_name: str = None
    description: str = None
    columns: dict[str, ColumnMetadata] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


JULY_TRANSACTIONS_METADATA = TableMetadata(
    table_name="july_transactions_2026",
    description="Fuel dispensing transactions for a waste management company operating in Lahore, Pakistan. Each row is one fuel purchase made with a fuel card at a filling station, covering 1–23 July 2026. Fuel is dispensed to municipal waste-collection vehicles and equipment across the city's towns and depots.",
    columns={
        "id": ColumnMetadata(
            description="Surrogate primary key. No business meaning.",
            show_samples=False,
        ),
        "town_code": ColumnMetadata(
            description="Short internal code for the town or depot. Prefer town_name for filtering.",
        ),
        "town_name": ColumnMetadata(
            description="Readable name of the town or depot where fuel was dispensed. Use this column for any question that names a location.",
        ),
        "txn_date": ColumnMetadata(
            description="Calendar date of the transaction.",
            show_samples=False,
        ),
        "txn_time": ColumnMetadata(
            description="Clock time of the transaction, no date part.",
            show_samples=False,
        ),
        "txn_at": ColumnMetadata(
            description="Date and time combined. Use for any question involving both.",
            show_samples=False,
        ),
        "card_number": ColumnMetadata(
            description="Fuel card identifier. Stored as text; never do arithmetic on it.",
            is_sensitive=True,
            show_samples=False,
        ),
        "category": ColumnMetadata(
            description="Raw vehicle or equipment type as recorded. Inconsistent spelling and casing. Prefer category_clean.",
            show_samples=False,
        ),
        "category_clean": ColumnMetadata(
            description="Standardised vehicle or equipment type. Use this column for any question about vehicle types.",
        ),
        "card_holder": ColumnMetadata(
            description="Name of the person holding the fuel card.",
            is_sensitive=True,
            show_samples=False,
        ),
        "merchant": ColumnMetadata(
            description="Filling station where fuel was purchased. 113 distinct names.",
            show_samples=True,
        ),
        "quantity_litres": ColumnMetadata(
            description="Volume of fuel dispensed, in litres.",
            show_samples=False,
        ),
        "product": ColumnMetadata(
            description="Fuel grade.",
        ),
        "rate_per_litre": ColumnMetadata(
            description="Price per litre in Pakistani Rupees at time of purchase.",
            show_samples=False,
        ),
        "amount": ColumnMetadata(
            description="Total transaction cost in Pakistani Rupees. Equals quantity_litres × rate_per_litre.",
            show_samples=False,
        ),
        "transaction_type": ColumnMetadata(
            description="Transaction type code. Constant across all rows.",
        ),
        "response": ColumnMetadata(
            description="Transaction outcome. Constant across all rows.",
        )
    },
    notes=[
        "Currency is Pakistani Rupees (PKR).",
        "The data covers 1–23 July 2026 only. Questions about other periods will return zero rows — write the query anyway and note the mismatch in assumptions.",
        "'response' is 'SUCCESSFULL' (note the double L) on every row. There are no failed transactions in this data. If asked about failures, say so rather than writing a query.",
        "'transaction_type' is 'S' on every row and cannot distinguish anything.",
        "Always prefer 'town_name' over 'town_code' and 'category_clean' over 'category'. The raw columns exist only for traceability.",
        "'merchant' values are free text with inconsistent spelling. When filtering by merchant, use ILIKE '%pattern%' rather than exact equality.",
        "'amount' already includes the full cost. Never multiply it by anything.",
        "Total fuel volume means SUM(quantity_litres). Total spend means SUM(amount). Average price per litre is best computed as SUM(amount) / SUM(quantity_litres), not AVG(rate_per_litre) — a plain average ignores transaction size and gives a subtly wrong figure.",
    ]
)

registry_table_metadata = {
    "july_transactions_2026": JULY_TRANSACTIONS_METADATA,
}


def get_table_metadata(table_name: str) -> TableMetadata:
    if table_name in registry_table_metadata:
        return registry_table_metadata[table_name]
    else:
        raise KeyError("Table is unknown to the registry.")