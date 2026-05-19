import os
import sqlite3
import json
import logging
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME", "gpt-5.2-chat")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-12-01-preview")
DB_FILE = 'reliance_data.db'

# Setup Azure OpenAI Client
client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=OPENAI_API_VERSION
)

def execute_sql(query):
    """Execute a SQL query against the SQLite database."""
    print(f"\n[Executing SQL] {query}")
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        # Limit results to avoid massive context
        result = [dict(row) for row in rows[:50]]
        if len(rows) > 50:
            result.append({"Note": f"Truncated {len(rows) - 50} rows."})
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

def generate_sales_quote(customer_no, items):
    """
    Generates a Sales Quote JSON file.
    items should be a list of dicts with 'product_id', 'quantity', 'price'
    """
    print(f"\n[Generating Quote] Customer: {customer_no}, Items: {len(items)}")
    quote = {
        "customer_no": customer_no,
        "items": items,
        "total_items": len(items),
        "status": "Draft",
        "generated_by": "AI Chatbot POC"
    }
    
    filename = f"Sales_Quote_{customer_no}.json"
    with open(filename, 'w') as f:
        json.dump(quote, f, indent=4)
        
    return json.dumps({"success": True, "file_created": filename, "message": f"Successfully created {filename}"})

tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": "Executes a SQL query against the reliance_data.db SQLite database. Use this to search for customers, products, and inventory. Tables available: PORTAL_CUSTOMER (CUST_NO, CUST_NAME, CUST_CITY, CUST_STATE), MDM_DIM_PRODUCT_MASTER_MV (PRODUCT_ID, PRODUCT_DESCRIPTION, COMMODITY, SHAPE), FCT_INVENTORY_MV (INVENTORY_ID, PRODUCT_ID, ON_HAND_WEIGHT, ON_HAND_AVAILABLE_WEIGHT, CUST_NO).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQLite query to execute."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_sales_quote",
            "description": "Generates a Sales Quote JSON file for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_no": {
                        "type": "string",
                        "description": "The customer number (CUST_NO)."
                    },
                    "items": {
                        "type": "array",
                        "description": "List of items to include in the quote.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "string"},
                                "quantity": {"type": "number"},
                                "price": {"type": "number"}
                            }
                        }
                    }
                },
                "required": ["customer_no", "items"]
            }
        }
    }
]

system_prompt = """
You are an intelligent AI assistant for Reliance Data. 
Your goal is to help the user query the database (SQLite) for customers, products, and inventory, and then generate Sales Quotes when requested.
You have access to a database with the following tables:
1. PORTAL_CUSTOMER: Contains customer info. Key fields: CUST_NO, CUST_NAME, CUST_CITY, CUST_STATE
2. MDM_DIM_PRODUCT_MASTER_MV: Contains product info. Key fields: PRODUCT_ID, PRODUCT_DESCRIPTION, COMMODITY, SHAPE
3. FCT_INVENTORY_MV: Contains inventory info. Key fields: INVENTORY_ID, PRODUCT_ID, CUST_NO, ON_HAND_WEIGHT, ON_HAND_AVAILABLE_WEIGHT

When asked to search, formulate a SQL query and use the `execute_sql` tool.
When asked to create a quote, gather the necessary info (Customer No, Product IDs, Quantities) and use the `generate_sales_quote` tool.
"""

def chat():
    print("Welcome to the Reliance AI Chatbot! (Type 'exit' to quit)")
    messages = [{"role": "system", "content": system_prompt}]
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit']:
            break
            
        messages.append({"role": "user", "content": user_input})
        
        try:
            response = client.chat.completions.create(
                model=DEPLOYMENT_NAME,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            messages.append(response_message)
            
            # Helper to parse potential manual JSON output from reasoning models
            manual_tool_name = None
            manual_tool_args = None
            
            if not response_message.tool_calls and response_message.content:
                # Look for JSON in the text
                import re
                # Find content that looks like JSON objects
                matches = re.finditer(r'\{[\s\S]*?\}', response_message.content)
                for match in matches:
                    try:
                        parsed = json.loads(match.group(0))
                        if "query" in parsed:
                            manual_tool_name = "execute_sql"
                            manual_tool_args = parsed
                            break
                        elif "customer_no" in parsed and "items" in parsed:
                            manual_tool_name = "generate_sales_quote"
                            manual_tool_args = parsed
                            break
                    except:
                        pass

            # Check if a tool call was made (standard or manual)
            if response_message.tool_calls or manual_tool_name:
                
                if response_message.tool_calls:
                    # Standard Tool Calling
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        if function_name == "execute_sql":
                            function_response = execute_sql(function_args.get("query"))
                        elif function_name == "generate_sales_quote":
                            function_response = generate_sales_quote(
                                function_args.get("customer_no"),
                                function_args.get("items")
                            )
                        else:
                            function_response = json.dumps({"error": "Unknown function"})
                            
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response
                        })
                else:
                    # Manual Tool Calling (from JSON parsing)
                    print(f"\n[Model Fallback] Detected manual tool call: {manual_tool_name}")
                    if manual_tool_name == "execute_sql":
                        function_response = execute_sql(manual_tool_args.get("query"))
                    elif manual_tool_name == "generate_sales_quote":
                        function_response = generate_sales_quote(
                            manual_tool_args.get("customer_no"),
                            manual_tool_args.get("items")
                        )
                    else:
                        function_response = json.dumps({"error": "Unknown manual function"})
                        
                    messages.append({
                        "role": "user",
                        "content": f"System Note: You requested a tool call manually. The result is:\n{function_response}"
                    })
                    
                # Get the final response from the model
                second_response = client.chat.completions.create(
                    model=DEPLOYMENT_NAME,
                    messages=messages
                )
                final_msg = second_response.choices[0].message
                messages.append(final_msg)
                print(f"\nAI: {final_msg.content}")
            else:
                print(f"\nAI: {response_message.content}")
                
        except Exception as e:
            print(f"\nError interacting with AI: {e}")

if __name__ == "__main__":
    chat()
