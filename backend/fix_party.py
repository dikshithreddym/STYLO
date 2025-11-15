#!/usr/bin/env python3
"""Fix party occasion logic to prioritize blazer"""

# Read file
with open('app/routers/suggestions.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the party section and replace it
output = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if we're at the party occasion
    if 'elif occasion == "party":' in line:
        # Write the header
        output.append(line)
        i += 1
        
        # Skip old comment and Dress line
        while i < len(lines) and ('# Prefer Dress' in lines[i] or 'add_if_found("Dress")' in lines[i]):
            if '# Prefer Dress' in lines[i]:
                output.append('        # Prefer Dress if available, otherwise try smart casual combo\n')
            elif 'add_if_found("Dress")' in lines[i]:
                output.append(lines[i])
            i += 1
        
        # Add if not result check
        output.append(lines[i])  # if not result:
        i += 1
        
        # Replace everything until the else: for casual
        output.append('            # Check if we have a blazer - if so, build a smart party outfit\n')
        output.append('            items = get_wardrobe_items(db)\n')
        output.append('            has_blazer = any(it for it in items if "blazer" in it["type"].lower() and it["id"] not in used)\n')
        output.append('            \n')
        output.append('            if has_blazer:\n')
        output.append('                # Smart party outfit: any top + chinos/jeans + blazer\n')
        output.append('                # Add a base top first\n')
        output.append('                if not add_if_found("Dress Shirt"):\n')
        output.append('                    # Use any top (T-shirt is fine under blazer for party)\n')
        output.append('                    top_items = [it for it in items if it.get("category") == "top" and it["id"] not in used]\n')
        output.append('                    if top_items:\n')
        output.append('                        result.append(top_items[0])\n')
        output.append('                        used.add(top_items[0]["id"])\n')
        output.append('                \n')
        output.append('                # Add chinos or nice pants\n')
        output.append('                if not add_if_found("Chinos"):\n')
        output.append('                    add_if_found("Jeans")\n')
        output.append('                \n')
        output.append('                # Add the blazer\n')
        output.append('                add_if_found("Blazer")\n')
        output.append('            else:\n')
        output.append('                # Casual party - no blazer available\n')
        output.append('                if not add_if_found("Dress Shirt"):\n')
        output.append('                    # Fallback to any nice top\n')
        output.append('                    top_items = [it for it in items if it.get("category") == "top" and it["id"] not in used]\n')
        output.append('                    if top_items:\n')
        output.append('                        result.append(top_items[0])\n')
        output.append('                        used.add(top_items[0]["id"])\n')
        output.append('                \n')
        output.append('                # Add bottoms - prefer Chinos/Jeans\n')
        output.append('                if not add_if_found("Chinos"):\n')
        output.append('                    if not add_if_found("Jeans"):\n')
        output.append('                        # Fallback to any bottom\n')
        output.append('                        bottom_items = [it for it in items if it.get("category") == "bottom" and it["id"] not in used]\n')
        output.append('                        if bottom_items:\n')
        output.append('                            result.append(bottom_items[0])\n')
        output.append('                            used.add(bottom_items[0]["id"])\n')
        
        # Skip the old party logic until we hit the else:
        while i < len(lines) and 'else:' not in lines[i]:
            i += 1
        continue
    
    output.append(line)
    i += 1

# Write back
with open('app/routers/suggestions.py', 'w', encoding='utf-8') as f:
    f.writelines(output)

print("Fixed party logic!")
