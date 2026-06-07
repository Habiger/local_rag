// src/components/DashboardLayout.tsx
"use client";

import React, { useState, useEffect } from 'react';
import { AppShell, Burger, Group, Text, Stack, Divider, NavLink, Tooltip, Badge } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconDatabase, IconFileText, IconCheck, IconX, IconActivity } from '@tabler/icons-react';
import { usePathname, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/axios'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [opened, { toggle }] = useDisclosure();
  const pathname = usePathname();
  const router = useRouter();

  // Mock Health States
  // const [servicesHealth] = useState({backend: 'online', docling: 'online', embedding: 'online' });
  const [servicesHealth, setServicesHealth] = useState({ backend: 'loading', docling: 'loading', embedding: 'loading' });

  useEffect(() => {
    let cancelled = false;

    const fetchHealth = async () => {
      try {
        const response = await apiClient.get('/health');
        if (!cancelled) {
          setServicesHealth({
            backend: response.data.backend || 'offline',
            docling: response.data.docling || 'offline',
            embedding: response.data.embedding || 'offline',
          });
        }
      } catch (error) {
        if (!cancelled) {
          setServicesHealth({ backend: 'offline', docling: 'offline', embedding: 'offline' });
        }
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);
  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 250, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
      bg="gray.0"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <IconDatabase size={28} color="#228be6" />
            <Text size="xl" fw={700} variant="gradient" gradient={{ from: 'blue', to: 'cyan', deg: 90 }}>
              RAG Admin
            </Text>
          </Group>
          <Group gap="xs" visibleFrom="sm">
            <Tooltip label="Backend Status">
              <Badge color={servicesHealth.backend === 'online' ? 'teal' : 'red'} variant="light" leftSection={servicesHealth.backend === 'online' ? <IconCheck size={12}/> : <IconX size={12}/>}>Backend</Badge>
            </Tooltip>
            <Tooltip label="Docling Server Status">
              <Badge color={servicesHealth.docling === 'online' ? 'teal' : 'red'} variant="light" leftSection={servicesHealth.docling === 'online' ? <IconCheck size={12}/> : <IconX size={12}/>}>Docling</Badge>
            </Tooltip>
            <Tooltip label="Embedding Server Status">
              <Badge color={servicesHealth.embedding === 'online' ? 'teal' : 'red'} variant="light" leftSection={servicesHealth.embedding === 'online' ? <IconCheck size={12}/> : <IconX size={12}/>}>Embeddings</Badge>
            </Tooltip>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <Stack gap="sm">
          <Text size="xs" fw={500} c="dimmed" tt="uppercase">Pipeline</Text>
          <NavLink
            label="PDF Upload & Deletion"
            leftSection={<IconFileText size="1rem" stroke={1.5} />}
            active={pathname === '/'}
            onClick={() => router.push('/')}
            variant="filled"
          />
          <NavLink
            label="Docling Conversion Progress"
            leftSection={<IconActivity size="1rem" stroke={1.5} />}
            active={pathname === '/progress'}
            onClick={() => router.push('/progress')}
            variant="filled"
          />
          <NavLink
            label="Pipeline Configuration"
            leftSection={<IconActivity size="1rem" stroke={1.5} />}
            active={pathname === '/configuration'}
            onClick={() => router.push('/configuration')}
            variant="filled"
          />
          <Divider my="sm" />
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main>
        {children}
      </AppShell.Main>
    </AppShell>
  );
}