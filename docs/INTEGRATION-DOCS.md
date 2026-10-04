# 📋 [Service Name] - Integration with [Platform] API

This document explains the [Platform] REST API endpoints required by the [Service Name] to extract [object type] data from [Platform] instances.

---

## 📋 Overview

The [Service Name] integrates with [Platform] REST API endpoints to extract [object type] information. Below are the required and optional endpoints:

### ✅ **Required Endpoint (Essential)**
| **API Endpoint**                    | **Purpose**                          | **Version** | **Required Permissions** | **Usage**    |
|-------------------------------------|--------------------------------------|-------------|--------------------------|--------------|
| `/[api_path]/[primary_endpoint]`    | Search and list [objects]           | [API_VERSION] | [Permission_Name]      | **Required** |

### 🔧 **Optional Endpoints (Advanced Features)**
| **API Endpoint**                    | **Purpose**                          | **Version** | **Required Permissions** | **Usage**    |
|-------------------------------------|--------------------------------------|-------------|--------------------------|--------------|
| `/[api_path]/[endpoint_1]`         | Get detailed [object] information   | [API_VERSION] | [Permission_Name]      | Optional     |
| `/[api_path]/[endpoint_2]`         | Get [object] [related_data]         | [API_VERSION] | [Permission_Name]      | Optional     |
| `/[api_path]/[endpoint_3]`         | Get [object] [configuration]        | [API_VERSION] | [Permission_Name]      | Optional     |
| `/[api_path]/[endpoint_4]`         | Get [object] [additional_data]      | [API_VERSION] | [Permission_Name]      | Optional     |

### 🎯 **Recommendation**
**Start with only the required endpoint.** The `/[primary_endpoint]` endpoint provides all essential [object] data needed for basic [object type] analytics and extraction.

---

## 🔐 Authentication Requirements

### **[Authentication Method] Authentication**
```http
[AUTH_HEADER]: [AUTH_FORMAT]
Content-Type: application/json
```

### **Required Permissions**
- **[Permission_1]**: [Description]
- **[Permission_2]**: [Description]

---

## 🌐 [Platform] API Endpoints

### 🎯 **PRIMARY ENDPOINT (Required for Basic [Object] Extraction)**

### 1. **Search [Objects]** - `/[api_path]/[primary_endpoint]` ✅ **REQUIRED**

**Purpose**: Get paginated list of all [objects] - **THIS IS ALL YOU NEED FOR BASIC [OBJECT] EXTRACTION**

**Method**: `GET`

**URL**: `https://{baseUrl}/[api_path]/[primary_endpoint]`

**Query Parameters**:
```
?[param1]=[value]&[param2]=[value]&[param3]=[value]
```

**Request Example**:
```http
GET https://[your_instance].[platform_domain]/[api_path]/[primary_endpoint]?[param1]=[value]&[param2]=[value]
[AUTH_HEADER]: [AUTH_VALUE]
Content-Type: application/json
```

**Response Structure** (Contains ALL essential [object] data):
```json
{
  "[pagination_start]": 0,
  "[pagination_size]": 50,
  "[pagination_total]": 75,
  "[pagination_last]": false,
  "[data_array]": [
    {
      "[field_id]": "[sample_id]",
      "[field_url]": "https://[your_instance].[platform_domain]/[api_path]/[primary_endpoint]/[sample_id]",
      "[field_name]": "[Sample Object Name]",
      "[field_type]": "[object_type]",
      "[nested_object]": {
        "[nested_field_1]": "[value_1]",
        "[nested_field_2]": "[value_2]",
        "[nested_field_3]": "[value_3]",
        "[nested_field_4]": "[value_4]",
        "[nested_field_5]": "[value_5]"
      }
    },
    {
      "[field_id]": "[sample_id_2]",
      "[field_url]": "https://[your_instance].[platform_domain]/[api_path]/[primary_endpoint]/[sample_id_2]", 
      "[field_name]": "[Another Sample Object]",
      "[field_type]": "[object_type_2]",
      "[nested_object]": {
        "[nested_field_1]": "[value_1]",
        "[nested_field_2]": "[value_2]",
        "[nested_field_3]": "[value_3]",
        "[nested_field_4]": "[value_4]",
        "[nested_field_5]": "[value_5]"
      }
    }
  ]
}
```

**✅ This endpoint provides ALL the default [object] fields:**
- [Field 1], [Field 2], [Field 3]
- [Field 4] URL
- [Nested Object] with [Sub-field 1], [Sub-field 2], [Sub-field 3]
- [Additional Field] and [Display Information]
- [Reference Field] for [related data]

**Rate Limit**: [X] requests per [time period]

---

## 🔧 **OPTIONAL ENDPOINTS (Advanced Features Only)**

> **⚠️ Note**: These endpoints are NOT required for basic [object] extraction. Only implement if you need advanced [object] analytics like [feature 1], [feature 2], or [feature 3].

### 2. **Get [Object] Details** - `/[api_path]/[endpoint_1]/{objectId}` 🔧 **OPTIONAL**

**Purpose**: Get detailed information for a specific [object]

**When to use**: Only if you need additional [object] metadata not available in search

**Method**: `GET`

**URL**: `https://{baseUrl}/[api_path]/[endpoint_1]/{objectId}`

**Request Example**:
```http
GET https://[your_instance].[platform_domain]/[api_path]/[endpoint_1]/[sample_id]
[AUTH_HEADER]: [AUTH_VALUE]
Content-Type: application/json
```

**Response Structure**:
```json
{
  "[field_id]": "[sample_id]",
  "[field_url]": "https://[your_instance].[platform_domain]/[api_path]/[endpoint_1]/[sample_id]",
  "[field_name]": "[Sample Object Name]",
  "[field_type]": "[object_type]",
  "[additional_field_1]": {
    "[sub_field_1]": [
      {
        "[property_1]": "[value_1]",
        "[property_2]": "[value_2]",
        "[property_3]": true
      }
    ],
    "[sub_field_2]": [
      {
        "[property_4]": "[value_4]",
        "[property_5]": "[value_5]"
      }
    ]
  },
  "[nested_object]": {
    "[nested_field_1]": "[value_1]",
    "[nested_field_2]": "[value_2]",
    "[nested_field_3]": "[value_3]",
    "[nested_field_4]": "[value_4]",
    "[nested_field_5]": "[value_5]"
  },
  "[boolean_field_1]": true,
  "[boolean_field_2]": false,
  "[boolean_field_3]": false
}
```

---

### 3. **Get [Object] [Related Data]** - `/[api_path]/[endpoint_2]/{objectId}/[related_endpoint]` 🔧 **OPTIONAL**

**Purpose**: Get [related data] associated with a [object]

**When to use**: Only if you need [related data] analysis and [specific metrics]

**Method**: `GET`

**URL**: `https://{baseUrl}/[api_path]/[endpoint_2]/{objectId}/[related_endpoint]`

**Query Parameters**:
```
?[param1]=[value]&[param2]=[value]&[filter_param]=[filter_value]
```

**Request Example**:
```http
GET https://[your_instance].[platform_domain]/[api_path]/[endpoint_2]/[sample_id]/[related_endpoint]?[param2]=[value]
[AUTH_HEADER]: [AUTH_VALUE]
Content-Type: application/json
```

**Response Structure**:
```json
{
  "[pagination_start]": 0,
  "[pagination_size]": 50,
  "[pagination_total]": 25,
  "[pagination_last]": false,
  "[data_array]": [
    {
      "[related_id]": 1,
      "[related_url]": "https://[your_instance].[platform_domain]/[api_path]/[related_endpoint]/1",
      "[related_status]": "[status_1]",
      "[related_name]": "[Related Item 1]",
      "[date_start]": "[date_format]",
      "[date_end]": "[date_format]",
      "[date_complete]": "[date_format]",
      "[date_created]": "[date_format]",
      "[origin_field]": "[sample_id]",
      "[description_field]": "[Description text]"
    },
    {
      "[related_id]": 2,
      "[related_url]": "https://[your_instance].[platform_domain]/[api_path]/[related_endpoint]/2",
      "[related_status]": "[status_2]", 
      "[related_name]": "[Related Item 2]",
      "[date_start]": "[date_format]",
      "[date_end]": "[date_format]",
      "[date_created]": "[date_format]",
      "[origin_field]": "[sample_id]",
      "[description_field]": "[Description text]"
    }
  ]
}
```

---

### 4. **Get [Object] Configuration** - `/[api_path]/[endpoint_3]/{objectId}/[config_endpoint]` 🔧 **OPTIONAL**

**Purpose**: Get [object] configuration details ([config_type_1], [config_type_2], [config_type_3])

**When to use**: Only if you need [workflow type] and [object] setup analysis

**Method**: `GET`

**URL**: `https://{baseUrl}/[api_path]/[endpoint_3]/{objectId}/[config_endpoint]`

**Request Example**:
```http
GET https://[your_instance].[platform_domain]/[api_path]/[endpoint_3]/[sample_id]/[config_endpoint]
[AUTH_HEADER]: [AUTH_VALUE]
Content-Type: application/json
```

**Response Structure**:
```json
{
  "[field_id]": "[sample_id]",
  "[field_name]": "[Sample Object Name]",
  "[field_type]": "[object_type]",
  "[field_url]": "https://[your_instance].[platform_domain]/[api_path]/[endpoint_3]/[sample_id]/[config_endpoint]",
  "[location_field]": {
    "[location_type]": "[location_value]",
    "[location_identifier]": "[identifier]"
  },
  "[filter_field]": {
    "[filter_id]": "[filter_value]",
    "[filter_url]": "https://[your_instance].[platform_domain]/[api_path]/[filter_endpoint]/[filter_value]"
  },
  "[config_object]": {
    "[config_array]": [
      {
        "[config_name]": "[Config Item 1]",
        "[config_values]": [
          {
            "[config_id]": "[id_1]",
            "[config_url]": "https://[your_instance].[platform_domain]/[api_path]/[status_endpoint]/[id_1]"
          }
        ]
      },
      {
        "[config_name]": "[Config Item 2]",
        "[config_values]": [
          {
            "[config_id]": "[id_2]",
            "[config_url]": "https://[your_instance].[platform_domain]/[api_path]/[status_endpoint]/[id_2]"
          }
        ]
      },
      {
        "[config_name]": "[Config Item 3]",
        "[config_values]": [
          {
            "[config_id]": "[id_3]",
            "[config_url]": "https://[your_instance].[platform_domain]/[api_path]/[status_endpoint]/[id_3]"
          }
        ]
      }
    ],
    "[constraint_type]": "[constraint_value]"
  },
  "[estimation_field]": {
    "[estimation_type]": "[estimation_value]",
    "[estimation_details]": {
      "[detail_id]": "[detail_value]",
      "[detail_name]": "[Detail Display Name]"
    }
  }
}
```

---

### 5. **Get [Object] [Additional Data]** - `/[api_path]/[endpoint_4]/{objectId}/[additional_endpoint]` 🔧 **OPTIONAL**

**Purpose**: Get [additional data] for a [object]

**When to use**: Only if you need [additional data] analysis and [specific functionality]

**Method**: `GET`

**URL**: `https://{baseUrl}/[api_path]/[endpoint_4]/{objectId}/[additional_endpoint]`

**Query Parameters**:
```
?[param1]=[value]&[param2]=[value]&[query_param]=[query_value]&[validation_param]=[validation_value]&[fields_param]=[field1],[field2],[field3],[field4]
```

**Request Example**:
```http
GET https://[your_instance].[platform_domain]/[api_path]/[endpoint_4]/[sample_id]/[additional_endpoint]?[param2]=[value]
[AUTH_HEADER]: [AUTH_VALUE]
Content-Type: application/json
```

**Response Structure**:
```json
{
  "[pagination_start]": 0,
  "[pagination_size]": 50,
  "[pagination_total]": 120,
  "[data_key]": [
    {
      "[item_id]": "[item_id_value]",
      "[item_key]": "[ITEM-123]",
      "[item_url]": "https://[your_instance].[platform_domain]/[api_path]/[item_endpoint]/[item_id_value]",
      "[item_fields]": {
        "[summary_field]": "[Item summary text]",
        "[status_field]": {
          "[status_id]": "[status_id_value]",
          "[status_name]": "[Status Name]",
          "[status_category]": {
            "[category_id]": 2,
            "[category_key]": "[category_key]",
            "[category_color]": "[color-name]"
          }
        },
        "[assignee_field]": {
          "[assignee_id]": "[assignee_account_id]",
          "[assignee_name]": "[Assignee Name]"
        },
        "[priority_field]": {
          "[priority_id]": "[priority_id_value]",
          "[priority_name]": "[Priority Level]"
        }
      }
    }
  ]
}
```

---

## 📊 Data Extraction Flow

### 🎯 **SIMPLE FLOW (Recommended - Using Only Required Endpoint)**

### **Single Endpoint Approach - `/[primary_endpoint]` Only**
```python
def extract_all_objects_simple():
    """Extract all [objects] using only the /[primary_endpoint] endpoint"""
    start_at = 0
    batch_size = 50
    all_objects = []
    
    while True:
        response = requests.get(
            f"{base_url}/[api_path]/[primary_endpoint]",
            params={
                "[pagination_param]": start_at,
                "[size_param]": batch_size
            },
            headers=auth_headers
        )
        
        data = response.json()
        objects = data.get("[data_array]", [])
        
        if not objects:  # No more objects
            break
            
        all_objects.extend(objects)
        
        # Check if this is the last page
        if data.get("[pagination_last]", True):
            break
            
        start_at += batch_size
    
    return all_objects

# This gives you ALL essential [object] data:
# - [field_id], [field_name], [field_type]
# - [nested_object] with [nested_field_1], [nested_field_2], [nested_field_3]
# - [field_url] for reference
```

---

### 🔧 **ADVANCED FLOW (Optional - Multiple Endpoints)**

> **⚠️ Only use this if you need [related_data], [configuration], or [additional_data] data**

### **Step 1: Batch [Object] Retrieval**
```python
# Get [objects] in batches of 50
for start_at in range(0, total_objects, 50):
    response = requests.get(
        f"{base_url}/[api_path]/[primary_endpoint]",
        params={
            "[pagination_param]": start_at,
            "[size_param]": 50
        },
        headers=auth_headers
    )
    objects_data = response.json()
    objects = objects_data.get("[data_array]", [])
```

### **Step 2: Enhanced [Object] Details (Optional)**
```python
# Get detailed information for each [object]
for obj in objects:
    response = requests.get(
        f"{base_url}/[api_path]/[endpoint_1]/{obj['[field_id]']}",
        headers=auth_headers
    )
    detailed_object = response.json()
```

### **Step 3: [Object] [Related Data] (Optional)**
```python
# Get [related data] for each [specific type] [object]
for obj in objects:
    if obj['[field_type]'] == '[specific_type]':
        response = requests.get(
            f"{base_url}/[api_path]/[endpoint_2]/{obj['[field_id]']}/[related_endpoint]",
            params={"[param2]": 50},
            headers=auth_headers
        )
        object_related_data = response.json()
```

### **Step 4: [Object] Configuration (Optional)**
```python
# Get configuration for each [object]
for obj in objects:
    response = requests.get(
        f"{base_url}/[api_path]/[endpoint_3]/{obj['[field_id]']}/[config_endpoint]",
        headers=auth_headers
    )
    object_config = response.json()
```

---

## ⚡ Performance Considerations

### **Rate Limiting**
- **Default Limit**: [X] requests per [time period] per API token
- **Burst Limit**: [Y] requests per [time period] (short duration)
- **Best Practice**: Implement exponential backoff on [rate limit response code] responses

### **Batch Processing**
- **Recommended Batch Size**: [X] [objects] per request
- **Concurrent Requests**: Max [N] parallel requests ([objects] are complex objects)
- **Request Interval**: [X]ms between requests to stay under rate limits

### **Error Handling**
```http
# Rate limit exceeded
HTTP/[rate_limit_code] [Rate Limit Message]
Retry-After: [retry_seconds]

# Authentication failed  
HTTP/401 Unauthorized

# Insufficient permissions
HTTP/403 Forbidden

# [Object] not found
HTTP/404 Not Found
```

---

## 🔒 Security Requirements

### **API Token Permissions**

#### ✅ **Required (Minimum Permissions)**
```
Required Scopes:
- [scope_1] (for basic [object] information)
```

#### 🔧 **Optional (Advanced Features)**
```
Additional Scopes (only if using optional endpoints):
- [scope_2] (for [related data] information)
- [scope_3] (for [object] configuration)
```

### **User Permissions**

#### ✅ **Required (Minimum)**
The API token user must have:
- **[Permission_1]** global permission
- **[Permission_2]** permission

#### 🔧 **Optional (Advanced Features)**
Additional permissions (only if using optional endpoints):
- **[Permission_3]** permission (for [object] configuration details)
- **[Permission_4]** (for [additional data] access)

---

## 📈 Monitoring & Debugging

### **Request Headers for Debugging**
```http
[AUTH_HEADER]: [AUTH_VALUE]
Content-Type: application/json
User-Agent: [ServiceName]/1.0
X-Request-ID: [object]-scan-001-batch-1
```

### **Response Validation**
```python
def validate_object_response(object_data):
    required_fields = ["[field_id]", "[field_name]", "[field_type]", "[nested_object]"]
    for field in required_fields:
        if field not in object_data:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate [object] type
    if object_data["[field_type]"] not in ["[type_1]", "[type_2]"]:
        raise ValueError(f"Invalid [object] type: {object_data['[field_type]']}")
```

### **API Usage Metrics**
- Track requests per [time period]
- Monitor response times
- Log rate limit headers
- Track authentication failures

---

## 🧪 Testing API Integration

### **Test Authentication**
```bash
curl -X GET \
  "https://[your_instance].[platform_domain]/[api_path]/[auth_test_endpoint]" \
  -H "[AUTH_HEADER]: [AUTH_VALUE]" \
  -H "Content-Type: application/json"
```

### **Test [Object] Search**
```bash
curl -X GET \
  "https://[your_instance].[platform_domain]/[api_path]/[primary_endpoint]?[size_param]=5" \
  -H "[AUTH_HEADER]: [AUTH_VALUE]" \
  -H "Content-Type: application/json"
```

### **Test [Object] Details**
```bash
curl -X GET \
  "https://[your_instance].[platform_domain]/[api_path]/[endpoint_1]/{objectId}" \
  -H "[AUTH_HEADER]: [AUTH_VALUE]" \
  -H "Content-Type: application/json"
```

---

## 🚨 Common Issues & Solutions

### **Issue**: 401 Unauthorized
**Solution**: Verify [auth method] and [credential] combination
```bash
[verification_command]
```

### **Issue**: 403 Forbidden
**Solution**: Check user has "[Permission_1]" and "[Permission_2]" permissions

### **Issue**: [Rate Limit Code] Rate Limited
**Solution**: Implement retry with exponential backoff
```python
import time
import random

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait_time)
    raise Exception("Max retries exceeded")
```

### **Issue**: Empty [Object] List
**Solution**: Check if user has access to [parent objects] with [object type] [objects]

### **Issue**: Need [Related Data]/Configuration But Want to Keep It Simple**
**Solution**: Start with `/[primary_endpoint]` only. Add optional endpoints later if needed for advanced [object type] analytics

---

## 💡 **Implementation Recommendations**

### 🎯 **Phase 1: Start Simple (Recommended)**
1. Implement only `/[api_path]/[primary_endpoint]`
2. Extract basic [object] data ([field_id], [field_name], [field_type], [nested_object] info)
3. This covers 90% of [object type] analytics needs

### 🔧 **Phase 2: Add Advanced Features (If Needed)**
1. Add `/[api_path]/[endpoint_1]/{objectId}` for detailed [object] info
2. Add `/[api_path]/[endpoint_2]/{objectId}/[related_endpoint]` for [related data] analysis  
3. Add `/[api_path]/[endpoint_3]/{objectId}/[config_endpoint]` for [workflow type] analysis
4. Add `/[api_path]/[endpoint_4]/{objectId}/[additional_endpoint]` for [additional functionality]

### ⚡ **Performance Tip**
- **Simple approach**: 1 API call per [batch_size] [objects]
- **Advanced approach**: 1 + N API calls (N = number of [objects] for details)
- Start simple to minimize API usage and complexity!

---

## 📞 Support Resources

- **[Platform] API Documentation**: [API_DOCS_URL]
- **Rate Limiting Guide**: [RATE_LIMIT_DOCS_URL]
- **Authentication Guide**: [AUTH_DOCS_URL]
- **[Object Type] Permissions Reference**: [PERMISSIONS_DOCS_URL]