"use client";

import React, { useEffect, useState } from 'react';
import { apiClient } from '@/lib/axios';
import { Title, Text, Stack, Card, Table, Progress, Badge, Loader, Group, ActionIcon } from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';

interface DocumentProgress {
  pdf_name: string;
  conversion_status: string;
  total_pages: number;
  success_pages: number;
  failed_pages: number;
}

export default function ProgressPage() {
  const [documents, setDocuments] = useState<DocumentProgress[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchProgress = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/documents/progress');
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error("Failed to fetch progress:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProgress();
    
    const interval = setInterval(fetchProgress, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    if (!status) return 'gray';
    const lower = status.toLowerCase();
    if (lower.includes('failed')) return 'red';
    if (lower.includes('finished') || lower.includes('success')) return 'teal';
    if (lower.includes('progress') || lower.includes('pending') || lower.includes('processing')) return 'blue';
    return 'gray';
  };

  return (
    <Stack gap="lg" maw={1200} mx="auto" w="100%">
      <Group justify="space-between" align="flex-end">
        <div>
          <Title order={2} c="dark.8">Docling Conversion Progress</Title>
          <Text c="dimmed" size="sm">Monitor pagewise document layout conversion status</Text>
        </div>
        
        {/* FIX: Manually toggling the Loader child avoids the Mantine 'loading' prop hydration bug entirely */}
        <ActionIcon 
          variant="light" 
          color="blue" 
          size="lg" 
          onClick={loading ? undefined : fetchProgress} 
          style={{ cursor: loading ? 'default' : 'pointer' }}
        >
          {loading ? <Loader size={18} /> : <IconRefresh size={20} />}
        </ActionIcon>
      </Group>

      <Card shadow="sm" radius="md" withBorder>
        {loading && documents.length === 0 ? (
          <Stack align="center" py="xl"><Loader size="md" variant="dots" /></Stack>
        ) : (
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Document Name</Table.Th>
                <Table.Th w={160}>State</Table.Th>
                <Table.Th w={250}>Progress</Table.Th>
                <Table.Th>Pages Breakdown</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {documents.map((doc) => {
                const total = Number(doc.total_pages) || 0;
                const success = Number(doc.success_pages) || 0;
                const failed = Number(doc.failed_pages) || 0;
                
                const pending = Math.max(0, total - success - failed);

                const conversionPercentage = total > 0 
                  ? Math.round((success / total) * 100) 
                  : 0;

                return (
                  <Table.Tr key={doc.pdf_name}>
                    <Table.Td fw={500} style={{ wordBreak: 'break-word' }}>
                      {doc.pdf_name}
                    </Table.Td>
                    
                    <Table.Td>
                      <Badge color={getStatusColor(doc.conversion_status)}>
                        {(doc.conversion_status || 'UNKNOWN').replace(/_/g, ' ').toUpperCase()}
                      </Badge>
                    </Table.Td>
                    
                    <Table.Td>
                      <Group justify="space-between" mb={4} gap="xs">
                        <Text size="xs" c="dimmed">
                          {success} of {total} pages
                        </Text>
                        <Text size="xs" fw={700} c="indigo.7">
                          {conversionPercentage}%
                        </Text>
                      </Group>
                      <Progress 
                        value={conversionPercentage} 
                        color={failed > 0 && success === 0 ? 'red' : 'indigo'} 
                        size="sm" 
                        radius="xl" 
                      />
                    </Table.Td>

                    <Table.Td>
                      <Group gap="md">
                        <Group gap={6}>
                          <Badge variant="dot" color="teal" size="sm">
                            Success: {success}
                          </Badge>
                        </Group>

                        {failed > 0 && (
                          <Group gap={6}>
                            <Badge variant="dot" color="red" size="sm">
                              Failed: {failed}
                            </Badge>
                          </Group>
                        )}

                        {pending > 0 && (
                          <Group gap={6}>
                            <Badge variant="dot" color="blue" size="sm">
                              Pending: {pending}
                            </Badge>
                          </Group>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
              
              {documents.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={4} ta="center" py="xl" c="dimmed">
                    No documents currently undergoing conversion.
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}