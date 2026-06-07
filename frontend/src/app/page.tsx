"use client";

import React, { useEffect, useState } from 'react';
import { apiClient } from '@/lib/axios';
import { FileNode } from '@/types';
import FileTree from '@/components/FileTree';
import UploadZone from '@/components/UploadZone';
import { Group, Title, Text, Button, Card, Stack, TextInput, Loader, Box } from '@mantine/core';
import { IconSearch, IconFileText, IconPlayerPlay } from '@tabler/icons-react';
import { useRouter } from 'next/navigation';

export default function ConfigurationPage() {
  const [fileNodes, setFileNodes] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPdfs, setSelectedPdfs] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  
  const router = useRouter();

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/documents/tree');
      setFileNodes(Array.isArray(response.data) ? response.data : response.data.tree || []);
    } catch (error) {
      console.error("Failed to fetch document tree:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchFiles(); }, []);

  const handleStartProcessing = async () => {
    if (selectedPdfs.size === 0) return;
    setSubmitting(true);
    try {
      await apiClient.post('/documents/process', {
        pdf_names: Array.from(selectedPdfs),
        pdf_indexing_config_id: 1 
      });
      router.push('/progress'); // Send user straight to the progress page!
    } catch (error) {
      console.error("Failed to start processing", error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Stack gap="lg" maw={1000} mx="auto" w="100%">
      <Group justify="space-between" align="flex-end">
        <div>
          <Title order={2} c="dark.8">Data Selection</Title>
          <Text c="dimmed" size="sm">Select directories or specific files to process in the RAG pipeline</Text>
        </div>
        <Button 
          leftSection={<IconPlayerPlay size={16} />} 
          color="blue" 
          onClick={handleStartProcessing}
          loading={submitting}
          disabled={selectedPdfs.size === 0}
        >
          Process {selectedPdfs.size > 0 ? `(${selectedPdfs.size})` : ''} Files
        </Button>
      </Group>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Card.Section withBorder inheritPadding py="xs">
          <Group justify="space-between" align="center">
            <Text fw={600} size="lg">Available Documents</Text>
            <Group gap="sm">
              <UploadZone compact onUploadSuccess={fetchFiles} />
              <TextInput
                placeholder="Search..."
                size="sm"
                leftSection={<IconSearch size={16} />}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                w={200}
              />
            </Group>
          </Group>
        </Card.Section>

        <Box mt="md" mih={300}>
          {loading ? (
            <Stack align="center" py="xl"><Loader size="md" variant="dots" /></Stack>
          ) : fileNodes.length > 0 ? (
            <FileTree 
              nodes={fileNodes} 
              searchQuery={searchQuery} 
              selectedPdfs={selectedPdfs}
              onSelectionChange={setSelectedPdfs}
            />
          ) : (
            <Stack align="center" py="xl" gap="xs">
              <IconFileText size={48} stroke={1} color="var(--mantine-color-gray-4)" />
              <Text size="sm" c="dimmed">No documents found. Upload some to begin.</Text>
            </Stack>
          )}
        </Box>
      </Card>
    </Stack>
  );
}