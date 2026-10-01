# ADR-0004: LaCie reference library is read-only and non-authoritative

Status: accepted.

The LaCie drive is historical proprietary reference material. The inventory tool
(`tools/lacie_inventory/`) opens files read-only, never writes inside the library path, and
records a catalog elsewhere. Catalog entries are classified with confidence and marked
`historical` by default. Nothing from the library may populate a CODE_PRODUCT_RULE without a
human promoting it and attaching a current authoritative source.
