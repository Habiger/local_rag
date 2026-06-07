def build_file_tree(records: list[dict]) -> list[dict]:
    """
    Converts a flat list of db records into a nested directory tree.
    Expected input: [{"pdf_name": "...", "original_path": "Folder/Sub/File.pdf"}, ...]
    """
    root = {"children": {}}
    
    for record in records:
        # e.g., "Marketing/PitchDecks/v2.pdf" -> ["Marketing", "PitchDecks", "v2.pdf"]
        path_parts = record.get("original_path", "").split("/")
        
        current_node = root
        current_path_accumulator = []
        
        for i, part in enumerate(path_parts):
            if not part:
                continue
                
            current_path_accumulator.append(part)
            full_path_str = "/".join(current_path_accumulator)
            is_file = (i == len(path_parts) - 1)
            
            if part not in current_node["children"]:
                current_node["children"][part] = {
                    "id": full_path_str,
                    "name": part,
                    "type": "file" if is_file else "folder",
                    "path": full_path_str,
                    "children": {} if not is_file else None
                }
            
            current_node = current_node["children"][part]

    # Recursive helper to convert nested dictionaries into lists
    def dict_to_list(node_dict):
        result = []
        for key, val in node_dict.items():
            node_format = {
                "id": val["id"],
                "name": val["name"],
                "type": val["type"],
                "path": val["path"]
            }
            if val["children"] is not None:
                # Sort folders first, then alphabetically, if desired
                node_format["children"] = dict_to_list(val["children"])
            result.append(node_format)
        
        # Sort so folders appear above files
        result.sort(key=lambda x: (x["type"] == "file", x["name"].lower()))
        return result

    return dict_to_list(root["children"])