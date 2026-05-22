#include "app_Communication.h"

uint8_t  gTCP_SendBuff[ETH_IPC_SEND_LEN]  = {0};
uint8_t  gUDP_SendBuff[ETH_UDP_SENDLEN]   = {0};

TimeOUT gOnLineCheck;     //超时检测
uint8_t UDP_RecvLen = 0;           //UDP数据长度
uint8_t UDP_RecvBuff[20] = {0};    //UDP接收缓冲区

extern ForceResult_t  fRes;

void NetWork_Register(void)  
{
	pDealUdpDataFunc = W5500_UDP_DataDispose;
  pDealTcpDataFunc = W5500_TCP_DataDispose;
}

void  W5500_UDP_DataDispose(uint8_t * buf, uint16_t len)
{

}

void  W5500_TCP_DataDispose(uint8_t * RecvBuff, uint16_t len)
{
	float oAdsData[7] = {0}; 
	if(RecvBuff[0] == 0x5A && RecvBuff[1] == 0xA5)  
	{
/*		oAdsData[0] = gAD1_Data.showAdsVal;                     
		oAdsData[1] = gAD2_Data.showAdsVal;                     
		oAdsData[2] = gAD3_Data.showAdsVal;  
    oAdsData[3] = gAD4_Data.showAdsVal;	*/
		memcpy(oAdsData,  volData,16);
		memcpy(oAdsData+4,&fRes.Fx,4);
		memcpy(oAdsData+5,&fRes.Fy,4);
		memcpy(oAdsData+6,&fRes.Fz,4);
		
		gTCP_SendBuff[0] = 0x5A;
    gTCP_SendBuff[1] = 0xA5;
    gTCP_SendBuff[2] = 0x81;
    gTCP_SendBuff[3] = 0x02;
    gTCP_SendBuff[4] = 29;
		memcpy(gTCP_SendBuff + 5, &oAdsData[0],4);               
		memcpy(gTCP_SendBuff + 9, &oAdsData[1],4);                 
		memcpy(gTCP_SendBuff + 13,&oAdsData[2],4);  
    memcpy(gTCP_SendBuff + 17,&oAdsData[3],4); 	
		memcpy(gTCP_SendBuff + 21,&oAdsData[4],4); 	
		memcpy(gTCP_SendBuff + 25,&oAdsData[5],4); 	
    memcpy(gTCP_SendBuff + 29,&oAdsData[6],4); 		
		SetCRCData(gTCP_SendBuff,  33);
		SendTcpData(gTCP_SendBuff, 35);
	}
	gOnLineCheck.IPC_OnLineFlag   = 0x01;
	gOnLineCheck.IPC_ResetFlag    = 0;
	gOnLineCheck.IPC_OffLineCount = 0;
	gOnLineCheck.IPC_ResetCnt     = 0;
}

void TCP_RecvDataReply(uint8_t Num,uint8_t target)
{

}

void TimeOut_Check(void)
{
	gOnLineCheck.IPC_OffLineCount++;
	
	if(gOnLineCheck.IPC_OffLineCount > IPC_TIMEOUT)     
	{
		gOnLineCheck.IPC_OffLineCount = 0;
		if(gOnLineCheck.IPC_OnLineFlag)
		{
			gOnLineCheck.IPC_OnLineFlag = 0;
			W5500_Init(); 
		}	
	}
}
/************************************************
** 工控机通讯断联处理
************************************************/
void IPC_OfflineDisPose(void)
{	
	if(gOnLineCheck.IPC_ResetCnt >= IPC_REINIT_TIME) // 2min
	{
		gOnLineCheck.IPC_ResetCnt = 0;
    W5500_Init();
	}
}

void SoftReset(void)
{ 
	__set_FAULTMASK(1); // 关闭所有中端
  NVIC_SystemReset(); // 复位
}

