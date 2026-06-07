"use client";

import React, { useMemo, useEffect, useRef } from "react";
import { Tree, Group, Text, useTree, TreeNodeData, RenderTreeNodePayload, Checkbox } from "@mantine/core";
import { IconFolder, IconFolderOpen, IconFileText } from "@tabler/icons-react";
import Fuse from "fuse.js";
import { FileNode } from "@/types";

interface FileTreeProps {
  nodes: FileNode[];
  searchQuery?: string;
  selectedPdfs: Set<string>;
  onSelectionChange: (newSelection: Set<string>) => void;
}

const flattenTree = (nodes: FileNode[]): FileNode[] => {
  let result: FileNode[] = [];
  for (const node of nodes) {
    result.push(node);
    if (node.children?.length) {
      result = result.concat(flattenTree(node.children));
    }
  }
  return result;
};

// ... keep escapeRegExp and highlightText helper functions the same ...
const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const highlightText = (text: string, highlight: string) => { /* keep original implementation */ return <>{text}</>; };

export default function FileTree({ nodes, searchQuery = "", selectedPdfs, onSelectionChange }: FileTreeProps) {
  const treeController = useTree();
  const previousSearchRef = useRef("");

  const filteredTreeData = useMemo(() => {
    const mapNode = (node: FileNode, filteredChildren?: TreeNodeData[]): TreeNodeData => ({
      value: String(node.id ?? node.name),
      label: node.name,
      children: filteredChildren ?? (node.children?.map((child) => mapNode(child)) || undefined),
      nodeProps: { type: node.type, originalNode: node }, // pass original node for recursion
    });

    const query = searchQuery.trim();
    if (!query) return nodes.map((node) => mapNode(node));

    const flatNodes = flattenTree(nodes);
    const fuse = new Fuse(flatNodes, { keys: ["name"], threshold: 0.3 });
    const results = fuse.search(query);
    const matchedIds = new Set(results.map((result) => result.item.id ?? result.item.name));

    const filterNode = (node: FileNode): TreeNodeData | null => {
      const nodeId = node.id ?? node.name;
      const isDirectMatch = matchedIds.has(nodeId);
      const filteredChildren = (node.children || []).map(filterNode).filter(Boolean) as TreeNodeData[];

      if (isDirectMatch || filteredChildren.length > 0) {
        return mapNode(node, filteredChildren.length > 0 ? filteredChildren : undefined);
      }
      return null;
    };
    return nodes.map(filterNode).filter(Boolean) as TreeNodeData[];
  }, [nodes, searchQuery]);

  useEffect(() => {
    const currentQuery = searchQuery.trim();
    if (currentQuery && currentQuery !== previousSearchRef.current) {
      treeController.expandAllNodes();
    }
    previousSearchRef.current = currentQuery;
  }, [searchQuery]);

  // Recursively extract all PDF names from a given node
  const getLeafPdfNames = (node: FileNode): string[] => {
    if (node.name.endsWith(".pdf")) return [node.name];
    if (!node.children) return [];
    return node.children.flatMap(getLeafPdfNames);
  };

  const renderNode = ({ node, expanded, hasChildren, elementProps }: RenderTreeNodePayload) => {
    const isFolder = node.nodeProps?.type === "folder" || hasChildren;
    const originalNode = node.nodeProps?.originalNode as FileNode;
    
    // Determine checkbox state
    const leafPdfs = getLeafPdfNames(originalNode);
    const allSelected = leafPdfs.length > 0 && leafPdfs.every(pdf => selectedPdfs.has(pdf));
    const someSelected = leafPdfs.length > 0 && leafPdfs.some(pdf => selectedPdfs.has(pdf));

    const handleCheck = (e: React.ChangeEvent<HTMLInputElement>) => {
      e.stopPropagation(); // Prevent expanding/collapsing folder
      const nextSelection = new Set(selectedPdfs);
      if (allSelected) {
        leafPdfs.forEach(pdf => nextSelection.delete(pdf));
      } else {
        leafPdfs.forEach(pdf => nextSelection.add(pdf));
      }
      onSelectionChange(nextSelection);
    };

    return (
      <Group gap="xs" {...elementProps} style={{ cursor: isFolder ? "pointer" : "default" }} onClick={(e) => {
        // Only trigger folder expand if clicking outside the checkbox
        elementProps.onClick?.(e as any);
      }}>
        <Checkbox 
          checked={allSelected} 
          indeterminate={someSelected && !allSelected} 
          onChange={handleCheck}
          onClick={(e) => e.stopPropagation()}
        />
        {isFolder ? (
          expanded ? <IconFolderOpen size={18} color="var(--mantine-color-blue-5)" /> : <IconFolder size={18} color="var(--mantine-color-blue-5)" />
        ) : (
          <IconFileText size={18} color="var(--mantine-color-gray-5)" />
        )}
        <Text size="sm" fw={isFolder ? 500 : 400} c={isFolder ? "dark.8" : "gray.7"}>
          {node.label}
        </Text>
      </Group>
    );
  };

  return <Tree data={filteredTreeData} tree={treeController} renderNode={renderNode} levelOffset={23} expandOnClick={true} />;
}