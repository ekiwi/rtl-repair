module i2c_master_bit_ctrl
(
  input clk,
  input rst,
  input nReset,
  input ena,
  input [15:0] clk_cnt,
  input [3:0] cmd,
  output reg cmd_ack,
  output reg busy,
  output reg al,
  input din,
  output reg dout,
  input scl_i,
  output scl_o,
  output reg scl_oen,
  input sda_i,
  output sda_o,
  output reg sda_oen
);

  reg [1:0] cSCL;reg [1:0] cSDA;
  reg [2:0] fSCL;reg [2:0] fSDA;
  reg sSCL;reg sSDA;
  reg dSCL;reg dSDA;
  reg dscl_oen;
  reg sda_chk;
  reg clk_en;
  reg slave_wait;
  reg [15:0] cnt;
  reg [13:0] filter_cnt;
  reg [17:0] c_state;

  always @(posedge clk) dscl_oen <= #1 scl_oen;


  always @(posedge clk or negedge nReset) if(!nReset) slave_wait <= 1'b0; 
  else slave_wait <= scl_oen & ~dscl_oen & ~sSCL | slave_wait & ~sSCL;

  wire scl_sync;assign scl_sync = dSCL & ~sSCL & scl_oen;

  always @(posedge clk or negedge nReset) if(~nReset) begin
    cnt <= #1 16'h0;
    clk_en <= #1 1'b1;
  end else if(rst || ~|cnt || !ena || scl_sync) begin
    cnt <= #1 clk_cnt;
    clk_en <= #1 1'b1;
  end else if(slave_wait) begin
    cnt <= #1 cnt;
    clk_en <= #1 1'b0;
  end else begin
    cnt <= #1 cnt - 16'h1;
    clk_en <= #1 1'b0;
  end


  always @(posedge clk or negedge nReset) if(!nReset) begin
    cSCL <= #1 2'b00;
    cSDA <= #1 2'b00;
  end else if(rst) begin
    cSCL <= #1 2'b00;
    cSDA <= #1 2'b00;
  end else begin
    cSCL <= { cSCL[0], scl_i };
    cSDA <= { cSDA[0], sda_i };
  end


  always @(posedge clk or negedge nReset) if(!nReset) filter_cnt <= 14'h0; 
  else if(rst || !ena) filter_cnt <= 14'h0; 
  else if(~|filter_cnt) filter_cnt <= clk_cnt >> 2; 
  else filter_cnt <= filter_cnt - 1;


  always @(posedge clk or negedge nReset) if(!nReset) begin
    fSCL <= 3'b111;
    fSDA <= 3'b111;
  end else if(rst) begin
    fSCL <= 3'b111;
    fSDA <= 3'b111;
  end else if(~|filter_cnt) begin
    fSCL <= { fSCL[1:0], cSCL[1] };
    fSDA <= { fSDA[1:0], cSDA[1] };
  end 


  always @(posedge clk or negedge nReset) if(~nReset) begin
    sSCL <= #1 1'b1;
    sSDA <= #1 1'b1;
    dSCL <= #1 1'b1;
    dSDA <= #1 1'b1;
  end else if(rst) begin
    sSCL <= #1 1'b1;
    sSDA <= #1 1'b1;
    dSCL <= #1 1'b1;
    dSDA <= #1 1'b1;
  end else begin
    sSCL <= #1 &fSCL[2:1] | &fSCL[1:0] | fSCL[2] & fSCL[0];
    sSDA <= #1 &fSDA[2:1] | &fSDA[1:0] | fSDA[2] & fSDA[0];
    dSCL <= #1 sSCL;
    dSDA <= #1 sSDA;
  end

  reg sta_condition;
  reg sto_condition;

  always @(posedge clk or negedge nReset) if(~nReset) begin
    sta_condition <= #1 1'b0;
    sto_condition <= #1 1'b0;
  end else if(rst) begin
    sta_condition <= #1 1'b0;
    sto_condition <= #1 1'b0;
  end else begin
    sta_condition <= #1 ~sSDA & dSDA & sSCL;
    sto_condition <= #1 sSDA & ~dSDA & sSCL;
  end


  always @(posedge clk or negedge nReset) if(!nReset) busy <= #1 1'b0; 
  else if(rst) busy <= #1 1'b0; 
  else busy <= #1 (sta_condition | busy) & ~sto_condition;

  reg cmd_stop;

  always @(posedge clk or negedge nReset) if(~nReset) cmd_stop <= #1 1'b0; 
  else if(rst) cmd_stop <= #1 1'b0; 
  else if(clk_en) cmd_stop <= #1 cmd == 4'b0010; 


  always @(posedge clk or negedge nReset) if(~nReset) al <= #1 1'b0; 
  else if(rst) al <= #1 1'b0; 
  else al <= #1 sda_chk & ~sSDA & sda_oen | |c_state & sto_condition & ~cmd_stop;


  always @(posedge clk) if(sSCL & ~dSCL) dout <= #1 sSDA; 

  parameter [17:0] idle = 18'b0_0000_0000_0000_0000;
  parameter [17:0] start_a = 18'b0_0000_0000_0000_0001;
  parameter [17:0] start_b = 18'b0_0000_0000_0000_0010;
  parameter [17:0] start_c = 18'b0_0000_0000_0000_0100;
  parameter [17:0] start_d = 18'b0_0000_0000_0000_1000;
  parameter [17:0] start_e = 18'b0_0000_0000_0001_0000;
  parameter [17:0] stop_a = 18'b0_0000_0000_0010_0000;
  parameter [17:0] stop_b = 18'b0_0000_0000_0100_0000;
  parameter [17:0] stop_c = 18'b0_0000_0000_1000_0000;
  parameter [17:0] stop_d = 18'b0_0000_0001_0000_0000;
  parameter [17:0] rd_a = 18'b0_0000_0010_0000_0000;
  parameter [17:0] rd_b = 18'b0_0000_0100_0000_0000;
  parameter [17:0] rd_c = 18'b0_0000_1000_0000_0000;
  parameter [17:0] rd_d = 18'b0_0001_0000_0000_0000;
  parameter [17:0] wr_a = 18'b0_0010_0000_0000_0000;
  parameter [17:0] wr_b = 18'b0_0100_0000_0000_0000;
  parameter [17:0] wr_c = 18'b0_1000_0000_0000_0000;
  parameter [17:0] wr_d = 18'b1_0000_0000_0000_0000;

  always @(posedge clk or negedge nReset) if(!nReset) begin
    c_state <= #1 idle;
    cmd_ack <= #1 1'b0;
    scl_oen <= #1 1'b1;
    sda_oen <= #1 1'b1;
    sda_chk <= #1 1'b0;
  end else if(rst | al) begin
    c_state <= #1 idle;
    cmd_ack <= #1 1'b0;
    scl_oen <= #1 1'b1;
    sda_oen <= #1 1'b1;
    sda_chk <= #1 1'b0;
  end else begin
    if(clk_en) case(c_state)
      idle: begin
        case(cmd)
          4'b0001: c_state <= #1 start_a;
          4'b0010: c_state <= #1 stop_a;
          4'b0100: c_state <= #1 wr_a;
          4'b1000: c_state <= #1 rd_a;
          default: c_state <= #1 idle;
        endcase
        scl_oen <= #1 scl_oen;
        sda_oen <= #1 sda_oen;
        sda_chk <= #1 1'b0;
      end
      start_a: begin
        c_state <= #1 start_b;
        scl_oen <= #1 scl_oen;
        sda_oen <= #1 1'b1;
        sda_chk <= #1 1'b0;
      end
      start_b: begin
        c_state <= #1 start_c;
        scl_oen <= #1 1'b1;
        sda_oen <= #1 1'b1;
        sda_chk <= #1 1'b0;
      end
      start_c: begin
        c_state <= #1 start_d;
        scl_oen <= #1 1'b1;
        sda_oen <= #1 1'b0;
        sda_chk <= #1 1'b0;
      end
      start_d: begin
        c_state <= #1 start_e;
        scl_oen <= #1 1'b1;
        sda_oen <= #1 1'b0;
        sda_chk <= #1 1'b0;
      end
      start_e: begin
        c_state <= #1 idle;
        cmd_ack <= #1 1'b1;
        scl_oen <= #1 1'b0;
        sda_oen <= #1 1'b0;
        sda_chk <= #1 1'b0;
      end
      stop_a: begin
        c_state <= #1 stop_b;
        scl_oen <= #1 1'b0;
        sda_oen <= #1 1'b0;
        sda_chk <= #1 1'b0;
      end
      stop_b: begin
        c_state <= #1 stop_c;
        scl_oen <= #1 1'b1;
        sda_oen <= #1 1'b0;
        sda_chk <= #1 1'b0;
      end
      stop_c: begin
        c_state <= #1 stop_d;
        scl_oen <= #1 1'b1;
        sda_oen <= #1 1'b0;
        sda_chk <= #1 1'b0;
      end
      stop_d: begin
        c_state <= #1 idle;
        cmd_ack <= #1 1'b1;
        scl_oen <= #1 1'b1;
        sda_oen <= #1 1'b1;
        sda_chk <= #1 1'b0;
      end
      rd_a: begin
        c_state <= #1 rd_b;
        scl_oen <= #1 1'b0;
        sda_oen <= #1 1'b1;
        sda_chk <= #1 1'b0;
      end
      rd_b: begin
        c_state <= #1 rd_c;
        scl_oen <= #1 1'b1;
        sda_oen <= #1 1'b1;
        sda_chk <= #1 1'b0;
      end
      rd_c: begin
        c_state <= #1 rd_d;
        scl_oen <= #1 1'b1;
        sda_oen <= #1 1'b1;
        sda_chk <= #1 1'b0;
      end
      rd_d: begin
        c_state <= #1 idle;
        cmd_ack <= #1 1'b1;
        scl_oen <= #1 1'b0;
        sda_oen <= #1 1'b1;
        sda_chk <= #1 1'b0;
      end
      wr_a: begin
        c_state <= #1 wr_b;
        scl_oen <= #1 1'b0;
        sda_oen <= #1 din;
        sda_chk <= #1 1'b0;
      end
      wr_b: begin
        c_state <= #1 wr_c;
        scl_oen <= #1 1'b1;
        sda_oen <= #1 din;
        sda_chk <= #1 1'b0;
      end
      wr_c: begin
        c_state <= #1 wr_d;
        scl_oen <= #1 1'b1;
        sda_oen <= #1 din;
        sda_chk <= #1 1'b1;
      end
      wr_d: begin
        c_state <= #1 idle;
        cmd_ack <= #1 1'b1;
        scl_oen <= #1 1'b0;
        sda_oen <= #1 din;
        sda_chk <= #1 1'b0;
      end
    endcase 
  end

  assign scl_o = 1'b0;
  assign sda_o = 1'b0;

endmodule
