import jinja2

template = '''
<domain type='kvm' id='3' xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>
  <name>{{ machine.name }}</name>
  <memory unit='GiB'>{{ machine.memsize }}</memory>
  <currentMemory unit='GiB'>{{ machine.memsize }}</currentMemory>
  <vcpu placement='static'>{{ machine.num_cpus }}</vcpu>
  <resource>
    <partition>/machine</partition>
  </resource>
  <os>
    <type arch='x86_64' machine='pc-i440fx-wily'>hvm</type>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
    <apic/>
     <vmport state='off'/>
  </features>
  <cpu mode='host-model'>
    <model fallback='allow'/>
  </cpu>
  <clock offset='utc'>
    <timer name='rtc' tickpolicy='catchup'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
  </clock>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>restart</on_crash>
  <pm>
    <suspend-to-mem enabled='no'/>
    <suspend-to-disk enabled='no'/>
  </pm>
  <devices>
    <emulator>/usr/bin/kvm-spice</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{{ machine.image }}'/>
      <backingStore/>
      <target dev='sda' bus='virtio'/>
      <alias name='virtio-disk0'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x08' function='0x0'/>
    </disk>

    {% for disk in machine.disks %}
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{{disk.image}}'/>
      <target dev='{{disk.device_name}}' bus='virtio'/>
      <serial>{{disk.serial}}</serial>
      <alias name='virtio-disk-{{disk.type}}'/>
    </disk>
    {% endfor %}

    <controller type='pci' index='0' model='pci-root'>
      <alias name='pci.0'/>
    </controller>
    <controller type='ide' index='0'>
      <alias name='ide'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x1'/>
    </controller>
    <controller type='virtio-serial' index='0'>
      <alias name='virtio-serial0'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x05' function='0x0'/>
    </controller>

    {% for iface in machine.net_ifaces %}
    {% if iface.mode == "isolated" %}
    <interface type='network'>
      <mac address='{{ iface.macaddress }}'/>
      <source network='{{ iface.source }}'/>
      <model type='virtio'/>
    </interface>
    {% else %}
    <interface type='direct'>
      <mac address='{{ iface.macaddress }}'/>
      <source dev='{{ iface.source }}' mode='bridge'/>
      <model type='virtio'/>
      <driver>
        <host csum='off' gso='off' tso4='off' tso6='off' ecn='off' ufo='off' mrg_rxbuf='off'/>
        <guest csum='off' tso4='off' tso6='off' ecn='off' ufo='off'/>
      </driver>
    </interface>
    {% endif %}
    {% endfor %}


    {% if machine.sol_port %}
    <serial type="tcp">
      <source mode="bind" host="0.0.0.0" service='{{ machine.sol_port }}'/>
      <protocol type="raw"/>
      <target port="0"/>
      <alias name='serial0'/>
    </serial>
    {% endif %}

    <channel type='spicevmc'>
      <target type='virtio' name='com.redhat.spice.0' state='disconnected'/>
      <alias name='channel0'/>
      <address type='virtio-serial' controller='0' bus='0' port='1'/>
    </channel>

    <input type='mouse' bus='ps2'/>
    <input type='keyboard' bus='ps2'/>

    <graphics type='vnc' autoport='yes' listen='0.0.0.0'>
      <listen type='address' address='0.0.0.0'/>
    </graphics>

    <video>
      <model type='cirrus' vram='16384' heads='1'/>
      <alias name='video0'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
    </video>

    {% for pci in machine.pcis %}
    <hostdev mode='subsystem' type='pci' managed='no'>
      <source>
        <address domain='0x{{ pci.domain }}' bus='0x{{ pci.bus }}' slot='0x{{ pci.slot }}' function='0x{{ pci.function }}'/>
      </source>
    </hostdev>
    {% endfor %}

    <memballoon model='virtio'>
      <alias name='balloon0'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x0'/>
    </memballoon>

  </devices>
</domain>'''


def generate_xml(machine):
    return jinja2.Template(template).render(machine=machine)
