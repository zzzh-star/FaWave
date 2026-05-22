#ifndef _APP_COMMUNICATION_H_
#define _APP_COMMUNICATION_H_

#include "common.h"

typedef struct
{
	uint16_t    IPC_ResetCnt;
	uint8_t     IPC_ResetFlag;
	uint8_t     IPC_OnLineFlag;            //工控机在线标识
	uint16_t    IPC_OffLineCount;
	
}TimeOUT;

extern TimeOUT         gOnLineCheck;

void  NetWork_Register(void);
void  W5500_TCP_DataDispose(uint8_t * buf, uint16_t len);
void  W5500_UDP_DataDispose(uint8_t * buf, uint16_t len);

void SoftReset(void);
void TimeOut_Check(void);
void TCP_RecvDataReply(uint8_t Num,uint8_t target);

void OffLineDispose(void);
void IPC_Reset(uint8_t mode);
void IPC_OfflineDisPose(void);

void W5500UDP_SendToUIScreen(void);
void W5500UDP_RecvFromUIScreen(uint8_t * RecvBuff);

#endif 


