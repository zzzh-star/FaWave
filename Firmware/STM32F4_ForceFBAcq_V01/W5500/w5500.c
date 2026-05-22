//*****************************************************************************
//
//! \file w5500.c
//! \brief W5500 HAL Interface.
//! \version 1.0.2
//! \date 2013/10/21
//! \par  Revision history
//!       <2014/05/01> V1.0.2
//!         1. Implicit type casting -> Explicit type casting. Refer to M20140501
//!            Fixed the problem on porting into under 32bit MCU
//!            Issued by Mathias ClauBen, wizwiki forum ID Think01 and bobh
//!            Thank for your interesting and serious advices.
//!       <2013/12/20> V1.0.1
//!         1. Remove warning
//!         2. WIZCHIP_READ_BUF WIZCHIP_WRITE_BUF in case _WIZCHIP_IO_MODE_SPI_FDM_
//!            for loop optimized(removed). refer to M20131220
//!       <2013/10/21> 1st Release
//! \author MidnightCow
//! \copyright
//!
//! Copyright (c)  2013, WIZnet Co., LTD.
//! All rights reserved.
//!
//! Redistribution and use in source and binary forms, with or without
//! modification, are permitted provided that the following conditions
//! are met:
//!
//!     * Redistributions of source code must retain the above copyright
//! notice, this list of conditions and the following disclaimer.
//!     * Redistributions in binary form must reproduce the above copyright
//! notice, this list of conditions and the following disclaimer in the
//! documentation and/or other materials provided with the distribution.
//!     * Neither the name of the <ORGANIZATION> nor the names of its
//! contributors may be used to endorse or promote products derived
//! from this software without specific prior written permission.
//!
//! THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
//! AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
//! IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
//! ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
//! LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
//! CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
//! SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
//! INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
//! CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
//! ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
//! THE POSSIBILITY OF SUCH DAMAGE.
//
//*****************************************************************************
//#include <stdio.h>
#include "common.h"
#include "socket.h"
#include "w5500.h"
#include "spi.h"
#include "drv_delay.h"
#include "dhcp.h"

#define USETCP 1

#define _W5500_SPI_VDM_OP_          0x00
#define _W5500_SPI_FDM_OP_LEN1_     0x01
#define _W5500_SPI_FDM_OP_LEN2_     0x02
#define _W5500_SPI_FDM_OP_LEN4_     0x03



//#define DHCP_ADDR 1

uint8_t peeraddr[] = {255, 255, 255, 255};

uint8_t broadcastaddr[] = {192, 168, 1, 255};
uint16_t work_port = 16006;
uint16_t peer_port = 16006;

extern uint8_t W5500_Interrupt;
uint8_t S0_State = 0;
#define SOCK_TCPS        0

#if DHCP_ADDR
  #define DATA_BUF_SIZE   1024
#endif 

#define RECV_BUF_SIZE   2048

/* Private macro -------------------------------------------------------------*/
#if DHCP_ADDR
 uint8_t gDATABUF[DATA_BUF_SIZE];
#endif 
// Default Network Configuration
wiz_NetInfo gWIZNETINFO = { .mac = {0x00, 0x08, 0xdc, SOURDEV, 0xab, 0xcd},
                            .ip = {192, 168, 1, SOURADDR},
                            .sn = {255, 255, 255, 0},
                            .gw = {192, 168, 1, 1},
                            .dns = {0, 0, 0, 0},
                            .dhcp = NETINFO_STATIC
                          };

uint8_t  udpnetpeeraddr1[] = {255, 255, 255, 255};
uint8_t  netpeeraddr2[]    = {255, 255, 255, 255};
uint8_t  UDP_TargetIP[]    = {192, 168, 1, UDP_TAR_IP};
uint8_t  UDP_DebugIP[]     = {192, 168, 1, UDP_DEBUG_IP};
uint16_t netpeer_port1     = 16006;
uint16_t netpeer_port2     = 16006;
uint8_t  netrecvbuf[RECV_BUF_SIZE];


DEALDATAFUN pDealUdpDataFunc = NULL;
DEALDATAFUN pDealTcpDataFunc = NULL;
uint8_t gTCPState = 0;      //增加TCP连接状态 jinliming 2023-09-21
int32_t retlen = 0;

W5500_Var  gW5500Var ={ .hasNetFlag = 0,
	                      .linkOKCount = 0,
                     };


										 
void SendTcpData(u8 *buf, u16 len)
{
  if(!gW5500Var.hasNetFlag)
    return;

  if(gTCPState == SOCK_ESTABLISHED)
  {
    send(SOCK_TCPS, buf, len);
  }
}

void SendUdpData(u8 *buf, u16 len, uint8_t * addr, uint16_t port)
{
  if(!gW5500Var.hasNetFlag)
    return;

  sendto(SOCK_UDPS, buf, len, addr, port);
}

void OnUdpRec(u8 *buf, u16 len)
{
  if(pDealUdpDataFunc != NULL)
  {
    pDealUdpDataFunc(buf, len);
  }
}


void OnTcpRec(u8 *buf, u16 len)
{
  if(pDealTcpDataFunc != NULL)
  {
    pDealTcpDataFunc(buf, len);
  }
}



void OnNetProc(void)
{
  retlen = getSn_RX_RSR(SOCK_UDPS);

  if(retlen > 0)
  {
    retlen = 0;
    retlen = recvfrom(SOCK_UDPS, netrecvbuf, RECV_BUF_SIZE, netpeeraddr2, &netpeer_port2);

    if(retlen > 0)
    {
      OnUdpRec(netrecvbuf, retlen);
    }
  }

#ifdef USETCP
  gTCPState = getSn_SR(SOCK_TCPS);

  switch(gTCPState)														  // 获取socket0的状态
  {
    case SOCK_INIT:															// Socket处于初始化完成(打开)状态
      listen(SOCK_TCPS);
      break;

    case SOCK_ESTABLISHED:											// Socket处于连接建立状态
      if(getSn_IR(SOCK_TCPS) & Sn_IR_CON)
      {
        setSn_IR(SOCK_TCPS, Sn_IR_CON);					// Sn_IR的CON位置1，通知W5500连接已建立
      }

      // 数据回环测试程序：数据从上位机服务器发给W5500，W5500接收到数据后再回给服务器
      retlen = getSn_RX_RSR(SOCK_TCPS);										// len=Socket0接收缓存中已接收和保存的数据大小

      if(retlen)
      {
				if(retlen<RECV_BUF_SIZE)
				{
					recv(SOCK_TCPS, netrecvbuf, retlen);

          OnTcpRec(netrecvbuf, retlen);
				}
      }

      break;

    case SOCK_CLOSE_WAIT:												    // Socket处于等待关闭状态
      disconnect(SOCK_TCPS);
      break;

    case SOCK_CLOSED:														    // Socket处于关闭状态
      socket(SOCK_TCPS, Sn_MR_TCP, TCPPORT, 0x00);	// 打开Socket0，打开一个本地端口
      break;
		
	//	SOCK_FIN_WAIT :
		//  socket(SOCK_TCPS, Sn_MR_TCP, TCPPORT, 0x00);	// 打开Socket0，打开一个本地端口
	//	break;
  }

  #endif

}

/**
  * @brief  Intialize the network information to be used in WIZCHIP
  * @retval None
  */
void network_init(void)
{
  u16 intmask = ((0x01 << 8) | 0xc0);

  ctlnetwork(CN_SET_NETINFO, (void*)&gWIZNETINFO);

  ctlwizchip(CW_SET_INTRMASK, (void*)&intmask);
}


extern uint8_t gUserLEDflag;

void W5500_Hardware_Reset(void)
{
  uint8_t tmp;
	W5500POWER(1); 
	vTaskDelay(50);
	W5500POWER(0);
	vTaskDelay(50);
  GPIO_ResetBits(W5500_RST_PORT, W5500_RST);//复位引脚拉低
	vTaskDelay(50);
  GPIO_SetBits(W5500_RST_PORT, W5500_RST);//复位引脚拉高

  for(tmp = 0; tmp < 5; tmp++)
  {

    if(gUserLEDflag)
    {
      gUserLEDflag = 0;
      DEBUGLED(1);  
    }
    else
    {
      gUserLEDflag = 1;
      DEBUGLED(0);

    }
    vTaskDelay(500);
  }

  //while((Read_W5500_1Byte(PHYCFGR)&LINK)==0);//等待以太网连接完成

  /* PHY link status check */
  do
  {
    if(ctlwizchip(CW_GET_PHYLINK, (void*)&tmp) == -1)
    {
      //printf("Unknown PHY Link stauts.\r\n");
    }

    if(tmp == PHY_LINK_ON)
    {
      gW5500Var.linkOKCount = 0;
			break;
    }
    else
    {
      gW5500Var.linkOKCount++;

      if(gW5500Var.linkOKCount > 3)
      {
        break;
      }
      GPIO_ResetBits(W5500_RST_PORT, W5500_RST);//复位引脚拉低
			vTaskDelay(60);
      GPIO_SetBits(W5500_RST_PORT, W5500_RST);//复位引脚拉高

      for(tmp = 0; tmp < 5; tmp++)
      {

        if(gUserLEDflag)
        {
          gUserLEDflag = 0;
          DEBUGLED(1);

        }
        else
        {
          gUserLEDflag = 1;
          DEBUGLED(0);

        }
       // delay_ms(500);
      }
    }
   vTaskDelay(200);
   // delay_ms(200);

  }
  while(1);
}


void my_ip_assign(void)
{
  //得到分配的IP地址，重新配置芯片的IP
  getIPfromDHCP(gWIZNETINFO.ip);
  getGWfromDHCP(gWIZNETINFO.gw);
  getSNfromDHCP(gWIZNETINFO.sn);
  getDNSfromDHCP(gWIZNETINFO.dns);
  gWIZNETINFO.dhcp = NETINFO_DHCP;

  ctlnetwork(CN_SET_NETINFO, (void*)&gWIZNETINFO);

  // printf("DHCP LEASED TIME : %d Sec.\r\n", getDHCPLeasetime());
}

void my_ip_conflict(void)
{
  // printf("CONFLICT IP from DHCP\r\n");
  while(1);
}

extern uint8_t gRTOS_Start;
void W5500_Init(void)
{
  uint8_t tmp;
//  uint8_t ret = 0;
  //uint16_t tmp2;

  //int32_t ret = 0;
  uint8_t memsize[2][8] = {{2, 2, 2, 2, 2, 2, 2, 2}, {2, 2, 2, 2, 2, 2, 2, 2}};


  SPI_Configuration();
  reg_wizchip_cris_cbfunc(SPI_CrisEnter, SPI_CrisExit);	//注册临界区函数
  reg_wizchip_cs_cbfunc(SPI_CS_Select, SPI_CS_Deselect);//注册SPI片选信号函数
  /* SPI Read & Write callback function */
  reg_wizchip_spi_cbfunc(SPI_ReadByte, SPI_WriteByte);	//注册读写函数

  /* WIZCHIP SOCKET Buffer initialize */
  if(ctlwizchip(CW_INIT_WIZCHIP, (void*)memsize) == -1)
  {
    //printf("WIZCHIP Initialized fail.\r\n");
   // while(1);
		while(1)
		{
			if(gRTOS_Start)
			{
				
        vTaskDelay(2);
			}	
		}
  }

  W5500_Hardware_Reset();
  W5500_Hardware_Reset();
	
  #ifdef DHCP_ADDR
  //dhcp addr
  setSHAR(gWIZNETINFO.mac);    // must be set the default mac before DHCP started， 设置MAC
  DHCP_init(1, gDATABUF); //DHCP准备工作，把除了MAC以外的参数都清零
  reg_dhcp_cbfunc(my_ip_assign, my_ip_assign, my_ip_conflict);//注册IP分配和冲突回调函数

  uint8_t dhcp_ret = DHCP_run();//重点是DHCP_run()，该函数实现动态申请IP的功能

  while((dhcp_ret != DHCP_IP_LEASED))//  && (dhcp_ret != DHCP_RUNNING))//返回DHCP_IP_LEASED说明申请租赁IP地址成功，如果没成功，重新申请
  {
    delay_ms(3000);
    dhcp_ret = DHCP_run();
  }

  //获取分配的各个参数
  uint8_t tmpstr[6];
  ctlnetwork(CN_GET_NETINFO, (void*)&gWIZNETINFO);
  ctlwizchip(CW_GET_ID, (void*)tmpstr);
  DHCP_stop();
  //dhcp addr

  #else
  //manual addr
  /* Network initialization */
  network_init();
  //manual addr
  #endif

//	//新建一个Socket并绑定本地端口5000
//	//ret = socket(SOCK_TCPS,Sn_MR_TCP,5000,0x00);
//	ret = socket(SOCK_TCPS,Sn_MR_UDP,work_port,0x00);
//	tmp = 0x1f;
//	ctlsocket(SOCK_TCPS ,CS_SET_INTMASK ,(void*)&tmp);
//	tmp = SOCK_IO_NONBLOCK;
//	ctlsocket(CS_SET_IOMODE ,CS_SET_IOMODE ,(void*)&tmp);	//



//	if(ret != SOCK_TCPS){
//		printf("%d:Socket Error\r\n",SOCK_TCPS);
//		while(1);
//	}else{
//		printf("%d:Opened\r\n",SOCK_TCPS);
//	}
//	//连接TCP服务器
//	ret = connect(SOCK_TCPS,DstIP,6000);
//	if(ret != SOCK_OK){
//		//printf("%d:Socket Connect Error\r\n",SOCK_TCPS);
//		while(1);
//	}

  //创建 一个UDP SOCKET
  socket(SOCK_UDPS, Sn_MR_UDP, UDPPORT, 0x00);
  tmp = 0x1f;
  ctlsocket(SOCK_UDPS, CS_SET_INTMASK, (void*)&tmp);
  tmp = SOCK_IO_NONBLOCK;
  ctlsocket(CS_SET_IOMODE, CS_SET_IOMODE, (void*)&tmp);	//

  gW5500Var.hasNetFlag = 1;

}

/*******************************************************************************
* 函数名  : W5500_Interrupt_Process
* 描述    : W5500中断处理程序框架
* 输入    : 无
* 输出    : 无
* 返回值  : 无
* 说明    : 无
*******************************************************************************/
void W5500_Interrupt_Process(void)
{
  unsigned char i, j;
  u16 retval = 0;
  //u16 tempval = 0;
  W5500_Interrupt = 0; //清零中断标志
  ctlwizchip(CW_GET_INTERRUPT, (void*)&retval);		//读取中断标志寄存器
IntDispose:
  ctlwizchip(CW_CLR_INTERRUPT, (void*)&retval);	//回写清除中断标志

  if((retval & IR_CONFLICT) == IR_CONFLICT)//IP地址冲突异常处理
  {
    //自己添加代码
    j = 1;
  }

  if((retval & IR_UNREACH) == IR_UNREACH)//UDP模式下地址无法到达异常处理
  {
    //自己添加代码
    j = 2;
  }

  i = (retval >> 8); //sir读取端口中断标志寄存器

  if((i & 0x01) == 0x01)//Socket0事件处理
  {
    ctlsocket(0, CS_GET_INTERRUPT, (void*)&j);
    ctlsocket(0, CS_CLR_INTERRUPT, (void*)&j);

//		j=Read_W5500_SOCK_1Byte(0,Sn_IR);//读取Socket0中断标志寄存器
//		Write_W5500_SOCK_1Byte(0,Sn_IR,j);
    if(j & Sn_IR_CON) //在TCP模式下,Socket0成功连接
    {
      S0_State |= Sn_IR_CON; //S_CONN;//网络连接状态0x02,端口完成连接，可以正常传输数据
    }

//		if(j&IR_DISCON)//在TCP模式下Socket断开连接处理
//		{
//			Write_W5500_SOCK_1Byte(0,Sn_CR,CLOSE);//关闭端口,等待重新打开连接
//			Socket_Init(0);		//指定Socket(0~7)初始化,初始化端口0
//			S0_State=0;//网络连接状态0x00,端口连接失败
//		}
    if(j & Sn_IR_SENDOK) //Socket0数据发送完成,可以再次启动S_tx_process()函数发送数据
    {
      S0_State |= Sn_IR_SENDOK;//S_TRANSMITOK;//端口发送一个数据包完成

    }

    if(j & Sn_IR_RECV) //Socket接收到数据,可以启动S_rx_process()函数
    {
      S0_State |= Sn_IR_RECV;//S_RECEIVE;//端口接收到一个数据包
    }

//		if(j&IR_TIMEOUT)//Socket连接或数据传输超时处理
//		{
//			Write_W5500_SOCK_1Byte(0,Sn_CR,CLOSE);// 关闭端口,等待重新打开连接
//			S0_State=0;//网络连接状态0x00,端口连接失败
//		}
  }

  ctlwizchip(CW_GET_INTERRUPT, (void*)&retval);

  if(retval != 0)
    goto IntDispose;
}


uint8_t  WIZCHIP_READ(uint32_t AddrSel)
{
  uint8_t ret;

  WIZCHIP_CRITICAL_ENTER();
  WIZCHIP.CS._select();

  #if( (_WIZCHIP_IO_MODE_ & _WIZCHIP_IO_MODE_SPI_))

  #if  ( _WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_SPI_VDM_ )
  AddrSel |= (_W5500_SPI_READ_ | _W5500_SPI_VDM_OP_);
#elif( _WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_SPI_FDM_ )
  AddrSel |= (_W5500_SPI_READ_ | _W5500_SPI_FDM_OP_LEN1_);
  #else
#error "Unsupported _WIZCHIP_IO_SPI_ in W5500 !!!"
  #endif

  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x00FF0000) >> 16);
  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x0000FF00) >>  8);
  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x000000FF) >>  0);
  ret = WIZCHIP.IF.SPI._read_byte();

  #elif ( (_WIZCHIP_IO_MODE_ & _WIZCHIP_IO_MODE_BUS_) )

  #if  (_WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_BUS_DIR_)

#elif(_WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_BUS_INDIR_)

  #else
#error "Unsupported _WIZCHIP_IO_MODE_BUS_ in W5500 !!!"
  #endif
  #else
#error "Unknown _WIZCHIP_IO_MODE_ in W5000. !!!"
  #endif

  WIZCHIP.CS._deselect();
  WIZCHIP_CRITICAL_EXIT();
  return ret;
}

void     WIZCHIP_WRITE(uint32_t AddrSel, uint8_t wb )
{
  WIZCHIP_CRITICAL_ENTER();
  WIZCHIP.CS._select();

  #if( (_WIZCHIP_IO_MODE_ & _WIZCHIP_IO_MODE_SPI_))

  #if  ( _WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_SPI_VDM_ )
  AddrSel |= (_W5500_SPI_WRITE_ | _W5500_SPI_VDM_OP_);
#elif( _WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_SPI_FDM_ )
  AddrSel |= (_W5500_SPI_WRITE_ | _W5500_SPI_FDM_OP_LEN1_);
  #else
#error "Unsupported _WIZCHIP_IO_SPI_ in W5500 !!!"
  #endif

  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x00FF0000) >> 16);
  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x0000FF00) >>  8);
  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x000000FF) >>  0);
  WIZCHIP.IF.SPI._write_byte(wb);

  #elif ( (_WIZCHIP_IO_MODE_ & _WIZCHIP_IO_MODE_BUS_) )

  #if  (_WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_BUS_DIR_)

#elif(_WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_BUS_INDIR_)

  #else
#error "Unsupported _WIZCHIP_IO_MODE_BUS_ in W5500 !!!"
  #endif
  #else
#error "Unknown _WIZCHIP_IO_MODE_ in W5500. !!!"
  #endif

  WIZCHIP.CS._deselect();
  WIZCHIP_CRITICAL_EXIT();
}

void     WIZCHIP_READ_BUF (uint32_t AddrSel, uint8_t* pBuf, uint16_t len)
{
  uint16_t i = 0;
  uint16_t j = 0;
  WIZCHIP_CRITICAL_ENTER();
  WIZCHIP.CS._select();

  #if( (_WIZCHIP_IO_MODE_ & _WIZCHIP_IO_MODE_SPI_))

  #if  ( _WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_SPI_VDM_ )
  AddrSel |= (_W5500_SPI_READ_ | _W5500_SPI_VDM_OP_);
  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x00FF0000) >> 16);
  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x0000FF00) >>  8);
  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x000000FF) >>  0);

  for(i = 0; i < len; i++, j)
    pBuf[i] = WIZCHIP.IF.SPI._read_byte();

#elif( _WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_SPI_FDM_ )
  AddrSel |= (_W5500_SPI_READ_ | _W5500_SPI_FDM_OP_LEN4_);

  for(i = 0; i < len / 4; i++, j)
  {
    WIZCHIP.IF.SPI._write_byte((AddrSel & 0x00FF0000) >> 16);
    WIZCHIP.IF.SPI._write_byte((AddrSel & 0x0000FF00) >>  8);
    WIZCHIP.IF.SPI._write_byte((AddrSel & 0x000000FF) >>  0);
    pBuf[i * 4]   = WIZCHIP.IF.SPI._read_byte();
    pBuf[i * 4 + 1] = WIZCHIP.IF.SPI._read_byte();
    pBuf[i * 4 + 2] = WIZCHIP.IF.SPI._read_byte();
    pBuf[i * 4 + 3] = WIZCHIP.IF.SPI._read_byte();
    AddrSel = WIZCHIP_OFFSET_INC(AddrSel, 4);
  }

  len %= 4;      // for the rest data
  // M20131220 : remove for loop
  i *= 4;

  if(len >= 2)
  {
    AddrSel -= 1;  // change _W5500_SPI_FDM_OP_LEN4_ to _W5500_SPI_FDM_OP_LEN2_

    //for(j = 0; j < len/2 ; j++)
    {
      WIZCHIP.IF.SPI._write_byte((AddrSel & 0x00FF0000) >> 16);
      WIZCHIP.IF.SPI._write_byte((AddrSel & 0x0000FF00) >>  8);
      WIZCHIP.IF.SPI._write_byte((AddrSel & 0x000000FF) >>  0);
      pBuf[i]   = WIZCHIP.IF.SPI._read_byte();
      pBuf[i + 1] = WIZCHIP.IF.SPI._read_byte();
      i += 2;
      AddrSel = WIZCHIP_OFFSET_INC(AddrSel, 2);
    }
  }

  len %= 2;

  if(len)
  {
    AddrSel -= 1;  // change _W5500_SPI_FDM_OP_LEN2_ to _W5500_SPI_FDM_OP_LEN1_
    WIZCHIP.IF.SPI._write_byte((AddrSel & 0x00FF0000) >> 16);
    WIZCHIP.IF.SPI._write_byte((AddrSel & 0x0000FF00) >>  8);
    WIZCHIP.IF.SPI._write_byte((AddrSel & 0x000000FF) >>  0);
    pBuf[i]   = WIZCHIP.IF.SPI._read_byte();
  }

  #else
#error "Unsupported _WIZCHIP_IO_MODE_SPI_ in W5500 !!!"
  #endif

  #elif ( (_WIZCHIP_IO_MODE_ & _WIZCHIP_IO_MODE_BUS_) )

  #if  (_WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_BUS_DIR_)

#elif(_WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_BUS_INDIR_)

  #else
#error "Unsupported _WIZCHIP_IO_MODE_BUS_ in W5500 !!!"
  #endif
  #else
#error "Unknown _WIZCHIP_IO_MODE_ in W5500. !!!!"
  #endif

  WIZCHIP.CS._deselect();
  WIZCHIP_CRITICAL_EXIT();
}

void     WIZCHIP_WRITE_BUF(uint32_t AddrSel, uint8_t* pBuf, uint16_t len)
{
  uint16_t i = 0;
  uint16_t j = 0;
  WIZCHIP_CRITICAL_ENTER();
  WIZCHIP.CS._select();

  #if( (_WIZCHIP_IO_MODE_ & _WIZCHIP_IO_MODE_SPI_))

  #if  ( _WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_SPI_VDM_ )
  AddrSel |= (_W5500_SPI_WRITE_ | _W5500_SPI_VDM_OP_);
  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x00FF0000) >> 16);
  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x0000FF00) >>  8);
  WIZCHIP.IF.SPI._write_byte((AddrSel & 0x000000FF) >>  0);

  for(i = 0; i < len; i++, j)
    WIZCHIP.IF.SPI._write_byte(pBuf[i]);

#elif( _WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_SPI_FDM_ )
  AddrSel |= (_W5500_SPI_WRITE_ | _W5500_SPI_FDM_OP_LEN4_);

  for(i = 0; i < len / 4; i++, j)
  {
    WIZCHIP.IF.SPI._write_byte((AddrSel & 0x00FF0000) >> 16);
    WIZCHIP.IF.SPI._write_byte((AddrSel & 0x0000FF00) >>  8);
    WIZCHIP.IF.SPI._write_byte((AddrSel & 0x000000FF) >>  0);
    WIZCHIP.IF.SPI._write_byte(pBuf[i * 4]  );
    WIZCHIP.IF.SPI._write_byte(pBuf[i * 4 + 1]);
    WIZCHIP.IF.SPI._write_byte(pBuf[i * 4 + 2]);
    WIZCHIP.IF.SPI._write_byte(pBuf[i * 4 + 3]);
    AddrSel = WIZCHIP_OFFSET_INC(AddrSel, 4);
  }

  len %= 4;      // for the rest data
  // M20131220 : Remove for loop
  i *= 4;

  if(len >= 2)
  {
    AddrSel -= 1;  // change _W5500_SPI_FDM_OP_LEN4_ to _W5500_SPI_FDM_OP_LEN2_

    //for(j = 0; j < len/2 ; j++)
    {
      WIZCHIP.IF.SPI._write_byte((AddrSel & 0x00FF0000) >> 16);
      WIZCHIP.IF.SPI._write_byte((AddrSel & 0x0000FF00) >>  8);
      WIZCHIP.IF.SPI._write_byte((AddrSel & 0x000000FF) >>  0);
      WIZCHIP.IF.SPI._write_byte(pBuf[i]  );
      WIZCHIP.IF.SPI._write_byte(pBuf[i + 1]);
      i += 2;
      AddrSel = WIZCHIP_OFFSET_INC(AddrSel, 2);
    }
    len %= 2;

    if(len)
    {
      AddrSel -= 1;  // change _W5500_SPI_FDM_OP_LEN2_ to _W5500_SPI_FDM_OP_LEN1_
      WIZCHIP.IF.SPI._write_byte((AddrSel & 0x00FF0000) >> 16);
      WIZCHIP.IF.SPI._write_byte((AddrSel & 0x0000FF00) >>  8);
      WIZCHIP.IF.SPI._write_byte((AddrSel & 0x000000FF) >>  0);
      WIZCHIP.IF.SPI._write_byte(pBuf[i]);
    }
  }

  #else
#error "Unsupported _WIZCHIP_IO_SPI_ in W5500 !!!"
  #endif

  #elif ( (_WIZCHIP_IO_MODE_ & _WIZCHIP_IO_MODE_BUS_) )

  #if  (_WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_BUS_DIR_)

#elif(_WIZCHIP_IO_MODE_ == _WIZCHIP_IO_MODE_BUS_INDIR_)

  #else
#error "Unsupported _WIZCHIP_IO_MODE_BUS_ in W5500 !!!"
  #endif
  #else
#error "Unknown _WIZCHIP_IO_MODE_ in W5500. !!!!"
  #endif

  WIZCHIP.CS._deselect();
  WIZCHIP_CRITICAL_EXIT();
}


uint16_t getSn_TX_FSR(uint8_t sn)
{
  uint16_t val = 0, val1 = 0;

  do
  {
    val1 = WIZCHIP_READ(Sn_TX_FSR(sn));
    val1 = (val1 << 8) + WIZCHIP_READ(WIZCHIP_OFFSET_INC(Sn_TX_FSR(sn), 1));

    if (val1 != 0)
    {
      val = WIZCHIP_READ(Sn_TX_FSR(sn));
      val = (val << 8) + WIZCHIP_READ(WIZCHIP_OFFSET_INC(Sn_TX_FSR(sn), 1));
    }
  }
  while (val != val1);

  return val;
}


uint16_t getSn_RX_RSR(uint8_t sn)
{
  uint16_t val = 0, val1 = 0;

  do
  {
    val1 = WIZCHIP_READ(Sn_RX_RSR(sn));
    val1 = (val1 << 8) + WIZCHIP_READ(WIZCHIP_OFFSET_INC(Sn_RX_RSR(sn), 1));

    if (val1 != 0)
    {
      val = WIZCHIP_READ(Sn_RX_RSR(sn));
      val = (val << 8) + WIZCHIP_READ(WIZCHIP_OFFSET_INC(Sn_RX_RSR(sn), 1));
    }
  }
  while (val != val1);

  return val;
}

void wiz_send_data(uint8_t sn, uint8_t *wizdata, uint16_t len)
{
  uint16_t ptr = 0;
  uint32_t addrsel = 0;

  if(len == 0)  return;

  ptr = getSn_TX_WR(sn);
  //M20140501 : implict type casting -> explict type casting
  //addrsel = (ptr << 8) + (WIZCHIP_TXBUF_BLOCK(sn) << 3);
  addrsel = ((uint32_t)ptr << 8) + (WIZCHIP_TXBUF_BLOCK(sn) << 3);
  //
  WIZCHIP_WRITE_BUF(addrsel, wizdata, len);

  ptr += len;
  setSn_TX_WR(sn, ptr);
}

void wiz_recv_data(uint8_t sn, uint8_t *wizdata, uint16_t len)
{
  uint16_t ptr = 0;
  uint32_t addrsel = 0;

  if(len == 0) return;

  ptr = getSn_RX_RD(sn);
  //M20140501 : implict type casting -> explict type casting
  //addrsel = ((ptr << 8) + (WIZCHIP_RXBUF_BLOCK(sn) << 3);
  addrsel = ((uint32_t)ptr << 8) + (WIZCHIP_RXBUF_BLOCK(sn) << 3);
  //
  WIZCHIP_READ_BUF(addrsel, wizdata, len);
  ptr += len;

  setSn_RX_RD(sn, ptr);
}


void wiz_recv_ignore(uint8_t sn, uint16_t len)
{
  uint16_t ptr = 0;
  ptr = getSn_RX_RD(sn);
  ptr += len;
  setSn_RX_RD(sn, ptr);
}

