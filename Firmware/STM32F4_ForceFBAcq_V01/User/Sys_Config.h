#ifndef _SYS_CONFIG_H_
#define _SYS_CONFIG_H_

#include "common.h"

#define   SYSTEM_SUPPORT_OS		 1		//定义是否支持RTOS

//---------------版本号----------------------------------------------------------------
#define   VER_NUM   "01.00.00"       
#define   VER_DATE  "2026.04.13"

//----------------以太网-------------------------------------------------------------------
#define   DESADDR              81
#define   DESDEV               0x81
#define   SOURADDR             82
#define   SOURDEV              0x82

#define   SOCK_TCPS            0
#define   SOCK_UDPS            2
#define   TCPPORT              16008

#define   ETH_RECV_LEN         16
#define   ETH_SEND_LEN         64

#define   ETH_IPC_RECV_LEN     6
#define   ETH_IPC_SEND_LEN     29

#define   ETH_IPC_DEBUG_LEN    29
#define   IPC_TIMEOUT          800      //工控机通讯超时时间
#define   IPC_REINIT_TIME      1800     //断线重连时间  

#define   UDP_TAR_IP           51
#define   UDP_DEBUG_IP         68       //调试输出信息IP
#define   UDPDBPORT            16068    //调试输出信息端口
#define   UDPPORT              16006
#define   ETH_UDP_SENDLEN      55       //UDP发送数据长度 
#define   UDP_SEND_ITV         9        //UDP发送间隔 
#define   ARM_REPWR_ON_TIM     833      //全臂断电重新恢复时间 (n秒 * 1000)/12 

extern  uint8_t gTCPState ;

typedef struct
{
	uint8_t udponlineflag;
	uint8_t udpofflinecount;
	uint8_t hasNetFlag;
	uint8_t linkOKCount;	
}W5500_Var;


#endif 


