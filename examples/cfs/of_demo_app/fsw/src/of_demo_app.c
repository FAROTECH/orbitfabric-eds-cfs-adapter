#include <string.h>

#include "cfe.h"
#include "cfe_core_api_base_msgids.h"
#include "cfe_mission_eds_designparameters.h"

#include "of_demo_eds_dictionary.h"
#include "of_demo_eds_dispatcher.h"
#include "of_demo_eds_typedefs.h"

#define OF_DEMO_APP_CMD_TOPIC_ID        EdsParam_CFE_MISSION_OF_DEMO_CMD_TOPICID
#define OF_DEMO_APP_STATUS_TLM_TOPIC_ID EdsParam_CFE_MISSION_OF_DEMO_STATUS_TLM_TOPICID
#define OF_DEMO_APP_CMD_PIPE_DEPTH      8
#define OF_DEMO_APP_CMD_PIPE_NAME       "OF_DEMO_CMD_PIPE"

typedef struct
{
    uint32_t                   RunStatus;
    CFE_SB_PipeId_t            CommandPipe;
    OF_DEMO_PayloadStatusTlm_t StatusTlm;
    uint32_t                   SampleCount;
    uint32_t                   PeriodMs;
} OF_DEMO_APP_Data_t;

static OF_DEMO_APP_Data_t OF_DEMO_APP_Data;

static void OF_DEMO_APP_LogStatusTlmMsgId(const char *Stage)
{
    CFE_SB_MsgId_t msg_id;
    CFE_Status_t   status;

    status = CFE_MSG_GetMsgId(CFE_MSG_PTR(OF_DEMO_APP_Data.StatusTlm.TelemetryHeader), &msg_id);
    if (status == CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("OF_DEMO_APP: %s status telemetry MID=0x%08lx\n",
                             Stage,
                             (unsigned long)CFE_SB_MsgIdToValue(msg_id));
    }
    else
    {
        CFE_ES_WriteToSysLog("OF_DEMO_APP: %s status telemetry MID read failed, RC=0x%08lx\n",
                             Stage,
                             (unsigned long)status);
    }
}

static int32_t OF_DEMO_APP_PayloadEnableCmd(const OF_DEMO_PayloadEnableCmd_t *Msg)
{
    CFE_Status_t status;

    (void)Msg;

    OF_DEMO_APP_LogStatusTlmMsgId("before payload update");

    OF_DEMO_APP_Data.StatusTlm.Payload.PayloadEnabled     = true;
    OF_DEMO_APP_Data.StatusTlm.Payload.PayloadSampleCount = OF_DEMO_APP_Data.SampleCount;

    OF_DEMO_APP_LogStatusTlmMsgId("before transmit");

    CFE_SB_TimeStampMsg(CFE_MSG_PTR(OF_DEMO_APP_Data.StatusTlm.TelemetryHeader));
    status = CFE_SB_TransmitMsg(CFE_MSG_PTR(OF_DEMO_APP_Data.StatusTlm.TelemetryHeader), true);

    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("OF_DEMO_APP: status telemetry transmit failed, RC=0x%08lx\n",
                             (unsigned long)status);
    }
    else
    {
        CFE_ES_WriteToSysLog("OF_DEMO_APP: payload.enable dispatched through generated EDS interface\n");
    }

    return status;
}

static int32_t OF_DEMO_APP_PayloadSetPeriodCmd(const OF_DEMO_PayloadSetPeriodCmd_t *Msg)
{
    OF_DEMO_APP_Data.PeriodMs = Msg->Payload.PeriodMs;

    CFE_ES_WriteToSysLog("OF_DEMO_APP: payload.set_period dispatched through generated EDS interface PeriodMs=%lu\n",
                         (unsigned long)OF_DEMO_APP_Data.PeriodMs);

    return CFE_SUCCESS;
}

static const EdsDispatchTable_EdsComponent_OF_DEMO_Application_CFE_SB_Telecommand_t OF_DEMO_APP_TC_DISPATCH_TABLE =
{
    .CMD =
    {
        .PayloadEnableCmd_indication    = OF_DEMO_APP_PayloadEnableCmd,
        .PayloadSetPeriodCmd_indication = OF_DEMO_APP_PayloadSetPeriodCmd
    }
};

static CFE_Status_t OF_DEMO_APP_Init(void)
{
    CFE_Status_t         status;
    CFE_SB_MsgId_t       cmd_msg_id;
    CFE_SB_MsgId_t       status_tlm_msg_id;
    CFE_SB_MsgId_Atom_t  cmd_mid_value;
    CFE_SB_MsgId_Atom_t  status_tlm_mid_value;

    memset(&OF_DEMO_APP_Data, 0, sizeof(OF_DEMO_APP_Data));
    OF_DEMO_APP_Data.RunStatus = CFE_ES_RunStatus_APP_RUN;

    status = CFE_EVS_Register(NULL, 0, CFE_EVS_EventFilter_BINARY);
    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("OF_DEMO_APP: event registration failed, RC=0x%08lx\n", (unsigned long)status);
        return status;
    }

    cmd_mid_value        = CFE_PLATFORM_CMD_TOPICID_TO_MIDV(OF_DEMO_APP_CMD_TOPIC_ID);
    status_tlm_mid_value = CFE_PLATFORM_TLM_TOPICID_TO_MIDV(OF_DEMO_APP_STATUS_TLM_TOPIC_ID);
    cmd_msg_id           = CFE_SB_ValueToMsgId(cmd_mid_value);
    status_tlm_msg_id    = CFE_SB_ValueToMsgId(status_tlm_mid_value);

    CFE_ES_WriteToSysLog("OF_DEMO_APP: mapped CMD topic %u -> MID 0x%08lx; STATUS_TLM topic %u -> MID 0x%08lx\n",
                         (unsigned int)OF_DEMO_APP_CMD_TOPIC_ID,
                         (unsigned long)cmd_mid_value,
                         (unsigned int)OF_DEMO_APP_STATUS_TLM_TOPIC_ID,
                         (unsigned long)status_tlm_mid_value);

    if (!CFE_SB_IsValidMsgId(cmd_msg_id))
    {
        CFE_ES_WriteToSysLog("OF_DEMO_APP: CMD topic %u mapped to invalid MID 0x%08lx\n",
                             (unsigned int)OF_DEMO_APP_CMD_TOPIC_ID,
                             (unsigned long)cmd_mid_value);
        return CFE_SB_BAD_ARGUMENT;
    }

    if (!CFE_SB_IsValidMsgId(status_tlm_msg_id))
    {
        CFE_ES_WriteToSysLog("OF_DEMO_APP: STATUS_TLM topic %u mapped to invalid MID 0x%08lx\n",
                             (unsigned int)OF_DEMO_APP_STATUS_TLM_TOPIC_ID,
                             (unsigned long)status_tlm_mid_value);
        return CFE_SB_BAD_ARGUMENT;
    }

    status = CFE_MSG_Init(CFE_MSG_PTR(OF_DEMO_APP_Data.StatusTlm.TelemetryHeader),
                          status_tlm_msg_id,
                          sizeof(OF_DEMO_APP_Data.StatusTlm));
    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("OF_DEMO_APP: status telemetry initialization failed, RC=0x%08lx\n",
                             (unsigned long)status);
        return status;
    }

    OF_DEMO_APP_LogStatusTlmMsgId("after CFE_MSG_Init");

    status = CFE_SB_CreatePipe(&OF_DEMO_APP_Data.CommandPipe,
                               OF_DEMO_APP_CMD_PIPE_DEPTH,
                               OF_DEMO_APP_CMD_PIPE_NAME);
    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("OF_DEMO_APP: command pipe creation failed, RC=0x%08lx\n", (unsigned long)status);
        return status;
    }

    status = CFE_SB_Subscribe(cmd_msg_id, OF_DEMO_APP_Data.CommandPipe);
    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("OF_DEMO_APP: command subscription failed, RC=0x%08lx\n", (unsigned long)status);
        return status;
    }

    CFE_ES_WriteToSysLog("OF_DEMO_APP: initialized with EDS CMD topic %u and STATUS_TLM topic %u\n",
                         (unsigned int)OF_DEMO_APP_CMD_TOPIC_ID,
                         (unsigned int)OF_DEMO_APP_STATUS_TLM_TOPIC_ID);

    return CFE_SUCCESS;
}

static void OF_DEMO_APP_TaskPipe(const CFE_SB_Buffer_t *SBBufPtr)
{
    CFE_Status_t status;

    status = EdsDispatch_EdsComponent_OF_DEMO_Application_Telecommand(SBBufPtr, &OF_DEMO_APP_TC_DISPATCH_TABLE);
    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("OF_DEMO_APP: generated EDS dispatch rejected command, RC=0x%08lx\n",
                             (unsigned long)status);
    }
}

void OF_DEMO_APP_Main(void)
{
    CFE_Status_t     status;
    CFE_SB_Buffer_t *SBBufPtr;

    status = OF_DEMO_APP_Init();
    if (status != CFE_SUCCESS)
    {
        OF_DEMO_APP_Data.RunStatus = CFE_ES_RunStatus_APP_ERROR;
    }

    while (CFE_ES_RunLoop(&OF_DEMO_APP_Data.RunStatus) == true)
    {
        status = CFE_SB_ReceiveBuffer(&SBBufPtr, OF_DEMO_APP_Data.CommandPipe, CFE_SB_PEND_FOREVER);
        if (status == CFE_SUCCESS)
        {
            OF_DEMO_APP_TaskPipe(SBBufPtr);
        }
        else
        {
            CFE_ES_WriteToSysLog("OF_DEMO_APP: command pipe receive failed, RC=0x%08lx\n",
                                 (unsigned long)status);
            OF_DEMO_APP_Data.RunStatus = CFE_ES_RunStatus_APP_ERROR;
        }
    }

    CFE_ES_ExitApp(OF_DEMO_APP_Data.RunStatus);
}
