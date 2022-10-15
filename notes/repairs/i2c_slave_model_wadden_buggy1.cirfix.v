module i2c_slave_model
(
  scl,
  sda
);

  parameter I2C_ADR = 7'b001_0000;
  input scl;
  inout sda;
  wire debug;assign debug = 1'b1;
  reg [7:0] mem [3:0];
  reg [7:0] mem_adr;
  reg [7:0] mem_do;
  reg sta;reg d_sta;
  reg sto;reg d_sto;
  reg [7:0] sr;
  reg rw;
  wire my_adr;
  wire i2c_reset;
  reg [2:0] bit_cnt;
  wire acc_done;
  reg ld;
  reg sda_o;
  wire sda_dly;
  parameter idle = 3'b000;
  parameter slave_ack = 3'b001;
  parameter get_mem_adr = 3'b010;
  parameter gma_ack = 3'b011;
  parameter data = 3'b100;
  parameter data_ack = 3'b101;
  reg [2:0] state;

  initial begin
    sda_o = 1'b1;
    state = idle;
  end


  always @(posedge scl) sr <= #1 { sr[6:0], sda };

  assign my_adr = sr[7:1] == I2C_ADR;

  always @(posedge scl) if(ld) bit_cnt <= #1 3'b111; 
  else bit_cnt <= #1 bit_cnt - 3'h1;

  assign acc_done = !(|bit_cnt);
  assign sda_dly = sda;

  always @(sda) if(scl) begin
    sta <= #1 1'b1;
    d_sta <= #1 1'b0;
    sto <= #1 1'b0;
    if(debug) $display("DEBUG i2c_slave; start condition detected at %t", $time); 
  end else sta <= #1 1'b0;


  always @(posedge scl) d_sta <= #1 sta;


  always @(posedge sda) if(scl) begin
    sta <= #1 1'b0;
    sto <= #1 1'b1;
    if(debug) $display("DEBUG i2c_slave; stop condition detected at %t", $time); 
  end else sto <= #1 1'b0;

  assign i2c_reset = sta || sto;

  always @(negedge scl or posedge sto) if(sto || sta && !d_sta) begin
    state <= #1 idle;
    sda_o <= #1 1'b1;
    ld <= #1 1'b1;
  end else begin
    sda_o <= #1 1'b1;
    ld <= #1 1'b0;
    case(state)
      idle: if(acc_done && my_adr) begin
        state <= #1 slave_ack;
        rw <= #1 sr[0];
        sda_o <= #1 1'b0;
        #2;
        if(debug && rw) $display("DEBUG i2c_slave; command byte received (read) at %t", $time); 
        if(debug && !rw) $display("DEBUG i2c_slave; command byte received (write) at %t", $time); 
        if(rw) begin
          mem_do <= #1 mem[mem_adr];
        end 
      end 
      slave_ack: begin
        if(rw) begin
          state <= #1 data;
          sda_o <= #1 mem_do[7];
        end else state <= #1 get_mem_adr;
        ld <= #1 1'b1;
      end
      get_mem_adr: if(acc_done) begin
        state <= #1 gma_ack;
        mem_adr <= #1 sr;
        sda_o <= #1 !(sr <= 15);
      end 
      gma_ack: begin
        state <= #1 data;
        ld <= #1 1'b1;
      end
      data: begin
        if(rw) sda_o <= #1 mem_do[7]; 
        if(acc_done) begin
          state <= #1 data_ack;
          mem_adr <= #2 mem_adr + 8'h1;
          sda_o <= #1 rw && (mem_adr <= 15);
          if(rw) begin
            #3 mem_do <= mem[mem_adr];
          end 
          if(!rw) begin
            mem[mem_adr[3:0]] <= #1 sr;
          end 
        end 
      end
      data_ack: begin
        ld <= #1 1'b1;
        if(rw) if(sr[0]) begin
          state <= #1 idle;
          sda_o <= #1 1'b1;
        end else begin
          state <= #1 data;
          sda_o <= #1 mem_do[7];
        end else begin
          state <= #1 data;
          sda_o <= #1 1'b1;
        end
      end
    endcase
  end


  always @(posedge scl) if(!acc_done && rw) mem_do <= #1 { mem_do[6:0], 1'b1 }; 

  assign sda = (sda_o)? 1'bz : 1'b0;
  wire tst_sto;assign tst_sto = sto;
  wire tst_sta;assign tst_sta = sta;

endmodule
