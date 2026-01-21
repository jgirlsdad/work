================================================================================
## 🚨 Top-Level Conversion Summary (MANDATORY FIXES)

This summary lists all critical gaps found. Fix these first to achieve v3.0 compliance.
| Status | Entity Type | Missing/Invalid Property | Required Action Summary |
| :--- | :--- | :--- | :--- |
| 🛑 | **Catalog** | `Dataset` | **Missing mandatory property: Dataset** |
| 🛑 | **Catalog** | `Description` | **Missing mandatory property: Description** |
| 🛑 | **Catalog** | `Publisher` | **Missing mandatory property: Publisher** |
| 🛑 | **Catalog** | `Title` | **Missing mandatory property: Title** |

================================================================================

## 🛠️ Part 1: Fix the Catalog (Top-Level Compliance)

This section details the gaps on the `dcat:Catalog` entity, which represents the `data.json` file itself.
### 🛑 Mandatory Catalog Gaps

| Requirement | Property URI | Definition | Status | Actionable Task |
| :--- | :--- | :--- | :--- | :--- |
| **Mandatory** | `Dataset` | Definition not found in SHACL file. This property is mandatory for compliance. | **OK ✅** | No action required. |
| **Mandatory** | `Description` | Definition not found in SHACL file. This property is mandatory for compliance. | **OK ✅** | No action required. |
| **Mandatory** | `Publisher` | Definition not found in SHACL file. This property is mandatory for compliance. | **OK ✅** | No action required. |
| **Mandatory** | `Title` | Definition not found in SHACL file. This property is mandatory for compliance. | **OK ✅** | No action required. |

---

## 🛠️ Part 2: Fix the Datasets (Content Compliance)

### 🛑 Mandatory Dataset Requirements

| Simple Name | Property URI | Definition |
| :--- | :--- | :--- |
| **Description** | `description` | Definition not found in SHACL file. This property is mandatory for compliance. |
| **Publisher** | `publisher` | Definition not found in SHACL file. This property is mandatory for compliance. |
| **Title** | `title` | Definition not found in SHACL file. This property is mandatory for compliance. |

================================================================================